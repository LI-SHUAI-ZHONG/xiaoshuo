"""Batch 36 regression tests: complete frontend rebuild + UI enhancements."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATIC = ROOT / 'src' / 'nw' / 'studio' / 'static'


# ── HTML structure integrity ──

def test_html_has_complete_app_shell():
    """index.html must have the v2 app-shell structure."""
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert 'app-shell' in html
    assert 'sidebar' in html
    assert 'main-stage' in html
    assert 'content-area' in html
    assert 'topbar' in html


def test_html_has_all_six_tabs():
    """index.html must have all 6 tab panels."""
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    for tab_id in ['tab-projects', 'tab-pipeline', 'tab-scenes', 'tab-cards', 'tab-materials', 'tab-routing']:
        assert tab_id in html, f'Missing tab: {tab_id}'


def test_html_has_search_overlay():
    """index.html must have the global search overlay."""
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert 'searchOverlay' in html
    assert 'searchInput' in html
    assert 'searchResults' in html


def test_html_has_notification_panel():
    """index.html must have the notification panel."""
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert 'notificationPanel' in html
    assert 'notificationList' in html


def test_html_has_modal_system():
    """index.html must have the modal dialog system."""
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert 'modalBackdrop' in html
    assert 'modalBody' in html
    assert 'modalFooter' in html


def test_html_has_theme_toggle():
    """index.html must have the theme toggle button."""
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert 'btnThemeToggle' in html
    assert 'data-theme' in html


def test_html_has_stats_row():
    """index.html must have the project stats dashboard."""
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert 'projectStatsRow' in html
    assert 'statChapters' in html
    assert 'statScenes' in html
    assert 'statCards' in html


def test_html_has_breadcrumb():
    """index.html must have the breadcrumb navigation."""
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert 'breadcrumb' in html
    assert 'breadcrumbPage' in html


# ── CSS design system ──

def test_css_has_design_system_variables():
    """styles.css must have CSS custom properties for the design system."""
    css = (STATIC / 'styles.css').read_text(encoding='utf-8')
    assert '--bg-app' in css
    assert '--accent' in css
    assert '--font-sans' in css
    assert '--radius' in css
    assert '--transition' in css


def test_css_has_light_theme():
    """styles.css must have a light theme override."""
    css = (STATIC / 'styles.css').read_text(encoding='utf-8')
    assert 'data-theme="light"' in css


def test_css_has_modal_styles():
    """styles.css must have modal dialog styles."""
    css = (STATIC / 'styles.css').read_text(encoding='utf-8')
    assert '.modal-backdrop' in css
    assert '.modal-box' in css


def test_css_has_search_overlay_styles():
    """styles.css must have search overlay styles."""
    css = (STATIC / 'styles.css').read_text(encoding='utf-8')
    assert '.search-overlay' in css
    assert '.search-box' in css


def test_css_has_notification_styles():
    """styles.css must have notification panel styles."""
    css = (STATIC / 'styles.css').read_text(encoding='utf-8')
    assert '.notification-panel' in css
    assert '.notification-item' in css


def test_css_has_loading_states():
    """styles.css must have loading spinner and skeleton styles."""
    css = (STATIC / 'styles.css').read_text(encoding='utf-8')
    assert '.loading-spinner' in css
    assert '.skeleton' in css


def test_css_has_responsive_breakpoints():
    """styles.css must have responsive media queries."""
    css = (STATIC / 'styles.css').read_text(encoding='utf-8')
    assert '@media' in css
    assert 'max-width: 768px' in css


def test_css_has_stat_card_styles():
    """styles.css must have stats dashboard card styles."""
    css = (STATIC / 'styles.css').read_text(encoding='utf-8')
    assert '.stat-card' in css
    assert '.stat-value' in css


def test_css_has_tooltip_styles():
    """styles.css must have tooltip styles."""
    css = (STATIC / 'styles.css').read_text(encoding='utf-8')
    assert 'data-tooltip' in css


# ── JS controller ──

def test_js_has_search_functionality():
    """app.js must have search overlay functions."""
    js = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert 'openSearch' in js
    assert 'closeSearch' in js
    assert 'performSearch' in js


def test_js_has_theme_toggle():
    """app.js must have theme toggle function."""
    js = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert 'toggleTheme' in js
    assert 'loadTheme' in js


def test_js_has_modal_system():
    """app.js must have modal dialog functions."""
    js = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert 'showModal' in js
    assert 'closeModal' in js


def test_js_has_notification_system():
    """app.js must have notification functions."""
    js = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert 'addNotification' in js
    assert 'renderNotifications' in js


def test_js_has_keyboard_shortcuts():
    """app.js must have keyboard shortcut setup."""
    js = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert 'setupKeyboard' in js
    assert 'Ctrl+K' in js or 'ctrlKey' in js


def test_js_has_sidebar_toggle():
    """app.js must have sidebar toggle function."""
    js = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert 'toggleSidebar' in js


def test_js_has_stats_dashboard():
    """app.js must have stats update function."""
    js = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert 'updateStats' in js


def test_js_has_loading_state_management():
    """app.js must have loading state management."""
    js = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert 'setLoading' in js
    assert 'loading-overlay' in js


# ── Batch 35 backward compatibility ──

def test_backward_compat_zen_reader():
    """Zen Reader elements must still exist (backward compat with Batch 35 tests)."""
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert 'zenReaderContainer' in html
    assert 'zenDiffContainer' in html
    assert 'btnZenDiff' in html
    assert 'btnZenRead' in html


def test_backward_compat_svg_graph():
    """SVG graph elements must still exist."""
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert 'svgGraphContainer' in html
    assert 'relationSvg' in html
    assert 'btnRenderGraph' in html


def test_backward_compat_job_stepper():
    """Job stepper elements must still exist."""
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert 'jobDrawerSection' in html
    assert 'jobStepperContent' in html
    assert 'btnRefreshJobs' in html


def test_backward_compat_js_functions():
    """Core JS functions from Batch 35 must still exist."""
    js = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert 'renderZenDiff' in js
    assert 'renderZenRead' in js
    assert 'simpleDiff' in js
    assert 'populateZenSelects' in js
    assert 'renderRelationshipGraph' in js
    assert 'refreshJobDrawer' in js
    assert 'JOB_STEPS' in js


def test_backward_compat_css_classes():
    """Core CSS classes from Batch 35 must still exist."""
    css = (STATIC / 'styles.css').read_text(encoding='utf-8')
    assert '.zen-reader-container' in css
    assert '.svg-graph-container' in css
    assert '.job-stepper-content' in css
    assert '.diff-add' in css
    assert '.node-circle' in css


# ── File sizes (sanity check that we actually enhanced) ──

def test_html_size_increased():
    """index.html should be larger than v1 (was ~596 lines)."""
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    line_count = len(html.splitlines())
    assert line_count > 400, f'HTML too small: {line_count} lines'


def test_css_size_increased():
    """styles.css should be larger than v1 (was ~702 lines)."""
    css = (STATIC / 'styles.css').read_text(encoding='utf-8')
    line_count = len(css.splitlines())
    assert line_count > 500, f'CSS too small: {line_count} lines'


def test_js_size_increased():
    """app.js should be larger than v1 (was ~1259 lines)."""
    js = (STATIC / 'app.js').read_text(encoding='utf-8')
    line_count = len(js.splitlines())
    assert line_count > 800, f'JS too small: {line_count} lines'
