"""Keep method placements intact when the workflow assembles real design cards."""
from nw.production_methods.contracts import at,require
from nw.task_models import canonical


def verify(candidate: dict,session: dict) -> None:
    if not session.get('production_method_policy'):return
    members={m['key']:m for m in candidate['members']}
    for record in session['stages']:
        products=record['products'];places=[]
        for app in products.get('_method_applications',[]):
            places.extend(p for output in app['outputs'] for p in output['placements'])
        places.extend(p for receipt in products.get('_method_receipts',[]) for p in receipt['placements'])
        for placement in places:
            path=placement['path'];expected=placement['value']
            if path[0]=='members':
                if len(path)==1:
                    actual=[members[m['key']] for m in products['members'] if m['key'] in members]
                else:
                    original=products['members'][path[1]];member=members.get(original['key'])
                    require(member is not None,'组装丢弃了方法生成的具体设计卡')
                    actual=at(member,path[2:]) if len(path)>2 else member
                require(canonical(actual)==canonical(expected),'组装修改了方法落点；须回到对应设计步骤补设计和回执，不能悄悄覆盖')
            elif path[0]=='directions' and len(path)>1:
                direction=products['directions'][path[1]]
                if canonical(direction)!=canonical(candidate['body']):continue
                actual=at(candidate['body'],path[2:]) if len(path)>2 else candidate['body']
                require(canonical(actual)==canonical(expected),'剧情方向与方法产物不一致')
