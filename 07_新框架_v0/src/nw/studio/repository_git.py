"""Conservative Git transport: scoped commits, fast-forward pulls, normal pushes."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import os
from pathlib import Path
import re
import subprocess
import tomllib
from typing import Iterator
from urllib.parse import urlsplit


class SyncError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def shared_config_safe(path: Path) -> None:
    data = tomllib.loads(path.read_text(encoding='utf-8'))
    if data.get('paths', {}).get('workspace') != 'workspace':
        raise SyncError('CONFIG', '共享 API 配置必须使用仓库内相对目录 workspace')
    specs = [data.get('model', {}), *(v for v in data.get('stage_models', {}).values() if isinstance(v, dict))]
    for spec in specs:
        if ('context_window_tokens' in spec and
                (type(spec['context_window_tokens']) is not int or spec['context_window_tokens'] <= 0)):
            raise SyncError('CONFIG', '模型窗口只接受正整数 token 数')
        if set(spec) - {'provider', 'base_url', 'model', 'api_key_env', 'timeout', 'params', 'context_window_tokens'}:
            raise SyncError('CONFIG_SECRET', 'API 配置含不支持的字段，未上传；只保存密钥环境变量名')
        name = spec.get('api_key_env', '')
        if name and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
            raise SyncError('CONFIG_SECRET', 'api_key_env 必须是环境变量名称')
        endpoint = urlsplit(spec.get('base_url', ''))
        if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
            raise SyncError('CONFIG_SECRET', 'API 地址不能包含凭据或查询密钥，未上传')
    allowed_by_provider = {
        'openai_compat': {'temperature', 'top_p', 'max_tokens', 'max_completion_tokens', 'seed', 'stop'},
        'ollama': {'temperature', 'top_p', 'top_k', 'num_predict', 'seed', 'stop', 'repeat_penalty'},
    }
    default_provider = data.get('model', {}).get('provider', 'openai_compat')
    param_pairs = [(default_provider, data.get('params', {})),
                   *((s.get('provider', default_provider), s.get('params', {})) for s in specs)]
    for prov, params in param_pairs:
        allowed = allowed_by_provider.get(prov)
        if allowed is None or (isinstance(params, dict) and set(params) - allowed):
            raise SyncError('CONFIG_SECRET', '共享配置含不支持的采样参数，未上传其他字段')
    if set(data) - {'model', 'params', 'paths', 'workflow', 'stage_models'}:
        raise SyncError('CONFIG_SECRET', 'API 配置含未识别的区段，未上传')


class GitRepository:
    def __init__(self, project: Path, remote: str, branch: str, *, allow_local: bool = False) -> None:
        self.project = project.resolve()
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', remote):
            raise SyncError('CONFIG', '无效的 Git 远程名称')
        if not branch or branch.startswith('-') or '..' in branch:
            raise SyncError('CONFIG', '无效的 Git 分支')
        self.remote, self.branch = remote, branch
        self.root = Path(self.run('rev-parse', '--show-toplevel', cwd=self.project)).resolve()
        relative = self.project.relative_to(self.root).as_posix()
        self.owned = (relative + '/studio.config.toml', relative + '/studio.repository.toml',
                      relative + '/studio_data/', '00_资料说明.md')
        url = self.run('remote', 'get-url', remote)
        if url.startswith('git@github.com:'):
            self.url = 'https://github.com/' + url.split(':', 1)[1].removesuffix('.git')
        else:
            parsed = urlsplit(url)
            self.url = 'https://github.com' + parsed.path.removesuffix('.git')
            if not allow_local and (parsed.scheme != 'https' or parsed.hostname != 'github.com'
                                    or parsed.username or parsed.password or parsed.query or parsed.fragment):
                raise SyncError('REMOTE', '自动同步仅连接当前配置的无明文凭据 GitHub 远程仓库')
        self.local_transport = allow_local
        self.run('check-ref-format', '--branch', branch)

    def run(self, *args: str, cwd: Path | None = None, check: bool = True, timeout: int = 40) -> str:
        env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'Never'}
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            result = subprocess.run(['git', '-c', 'core.quotePath=false', '-C', str(cwd or self.root), *args],
                                    capture_output=True, text=True, encoding='utf-8', errors='replace',
                                    timeout=timeout, env=env, creationflags=flags)
        except (OSError, subprocess.TimeoutExpired):
            raise SyncError('NETWORK', 'Git 命令未完成，请检查网络、Git 安装和 GitHub 登录') from None
        if check and result.returncode:
            message = result.stderr.strip() or result.stdout.strip() or 'Git 操作失败'
            message = re.sub(r'https://[^\s/@]+:[^\s/@]+@', 'https://[凭据已隐藏]@', message)
            raise SyncError('GIT', message[:1200])
        return result.stdout.strip() if check else str(result.returncode)

    def owns(self, path: str) -> bool:
        return any(path.startswith(p) if p.endswith('/') else path == p for p in self.owned)

    def check_workspace(self) -> None:
        if self.run('branch', '--show-current') != self.branch:
            raise SyncError('BRANCH', '当前分支与客户端同步分支不同，已暂停自动同步')
        for filename in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REBASE_HEAD'):
            if self.run('rev-parse', '--verify', '-q', filename, check=False) == '0':
                raise SyncError('CONFLICT', '仓库有尚未完成的合并或变基，已暂停自动同步')
        # Unrelated untracked directories never enter a client commit.
        paths = self.run('diff', 'HEAD', '--name-only', '-z').split('\x00')
        if any(p and not self.owns(p) for p in paths):
            raise SyncError('LOCAL_CHANGES', '仓库还有客户端配置/数据以外的未提交修改，已保留，请先完成这些修改')

    @contextmanager
    def exclusive(self, workspace: Path) -> Iterator[None]:
        path = workspace / '_git_sync' / 'transport.lock'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a+b') as stream:
            if stream.seek(0, 2) == 0:
                stream.write(b'\0')
                stream.flush()
            stream.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise SyncError('BUSY', '另一个客户端正在同步此仓库') from None
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def update_map(self) -> None:
        path = self.root / '00_资料说明.md'
        if not path.is_file():
            return
        text = path.read_text(encoding='utf-8')
        relative = self.project.relative_to(self.root).as_posix()
        files = set(self.run('ls-files', '-c', '-o', '--exclude-standard', '-z', '--', relative).split('\0')) - {''}
        size = sum((self.root / name).stat().st_size for name in files if (self.root / name).is_file())
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.startswith('| 07 |'):
                fields = line.split('|')
                fields[4], fields[5] = f' {len(files):,}（已跟踪及未忽略文件） ', f' {size:,} 字节 '
                lines[index] = '|'.join(fields)
        today = datetime.now().strftime('%Y-%m-%d')
        text = re.sub(r'最后更新：\d{4}-\d{2}-\d{2}', '最后更新：' + today, '\n'.join(lines))
        marker = '## 8. 更新规则'
        entry = f'- {today}｜客户端自动同步｜保存当前非密钥 API 配置、书库与正式小说资料；同步目标 GitHub {self.branch}。\n\n'
        if marker in text:
            text = text.replace(marker, entry + marker, 1)
        path.write_text(text + '\n', encoding='utf-8')

    def commit_data(self) -> bool:
        self.check_workspace()
        shared_config_safe(self.project / 'studio.config.toml')
        scoped = [p.rstrip('/') for p in self.owned[:-1] if (self.root / p.rstrip('/')).exists()]
        if not scoped:
            return False
        self.run('add', '--', *scoped)
        if self.run('diff', '--cached', '--quiet', '--', *scoped, check=False) == '0':
            return False
        self.update_map()
        if (self.root / '00_资料说明.md').is_file():
            self.run('add', '--', '00_资料说明.md')
        self.run('commit', '--quiet', '-m', 'studio: sync API settings and actual novel data')
        return True

    def fetch(self) -> str:
        self.run('fetch', '--quiet', '--no-tags', self.remote,
                 f'refs/heads/{self.branch}:refs/remotes/{self.remote}/{self.branch}', timeout=90)
        return self.run('rev-parse', f'refs/remotes/{self.remote}/{self.branch}')

    def integrate(self, remote_head: str) -> list[str]:
        self.check_workspace()
        local = self.run('rev-parse', 'HEAD')
        if local == remote_head:
            return []
        if self.run('merge-base', '--is-ancestor', remote_head, local, check=False) == '0':
            return []
        if self.run('merge-base', '--is-ancestor', local, remote_head, check=False) != '0':
            raise SyncError('DIVERGED', '本地和 GitHub 都有新提交，已保留双方版本；需要先处理分支冲突')
        changed = self.run('diff', '--name-only', '-z', local, remote_head).split('\0')
        self.run('merge', '--ff-only', '--quiet', remote_head)
        return [p for p in changed if p]

    def push(self) -> None:
        self.run('push', '--quiet', self.remote, f'HEAD:refs/heads/{self.branch}', timeout=300)
