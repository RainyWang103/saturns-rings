"""Render a fictional, offline delivery fixture through the actual template.

Usage: python tests/cases/travel-planner/render_delivery_fixture.py --output /tmp/preview.html
Use --template with a previous template to compare the same planning material.
No destinations, bookings or research results in this fixture are real.
"""
import argparse
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / 'shared/travel-planner/references/html-template.html'
INTRO = '虚构三日行程 · 仅检验模板，不可用于旅行或预订'
DAYS = [
    dict(date='6月12日', week='周六', city='青湾 · 抵达与河岸美术馆', hotel='河岸小院 Riverside House',
         stay='未订', night='1', stay_note='计划15:00后入住；行李寄存及房型待确认。',
         route=['青湾机场', '河岸小院', '河岸美术馆'],
         logic='抵达后先寄存行李与午餐，再进入美术馆；如延误超过60分钟，保留午餐与入住，缩短河岸散步。',
         anchor='抵达航班与接驳', anchor_time='09:20落地为虚构规划时间；尚无真实订单。',
         events=[
             dict(time='09:20–12:00', title='抵达与行李寄存', icon='plane', state='未订',
                  intro='在机场完成入境与取件，乘机场列车进入青湾。先到河岸小院寄存行李，避免带大件行李穿行展厅。',
                  execution='门到门预留2小时40分钟，含入境、候车、步行与寄存；12:00–13:00午餐。',
                  highlight='抵达日以恢复体力为主，河岸散步可随体力缩短。',
                  warning='如行李延误，先联系住宿确认寄存，再调整美术馆时段。'),
             dict(time='14:00–16:00', title='河岸美术馆 Museo delle Acque e della Luce', icon='art', state='候选',
                  intro='先看二层的窗边风景组画，再下楼看水面主题装置。对照画中笔触与真实窗光，留意同一片水面如何随观看位置变化。',
                  execution='建议停留2小时，13:40到入口；预约和行李限制待核，16:30返回住宿休息，18:30晚餐。',
                  highlight='重点比较三幅水景的反光处理，不必追求看完每间展室。',
                  warning='若无法预约，改走滨水雕塑步道；雨天改为酒店休息。')],
         backup='若抵达晚于11:00，取消雕塑步道，保留正餐和入住；不压缩晚间休息。',
         transfers=[
             ('青湾机场', '河岸小院', '机场列车＋步行', '45–60', '20', '12:00', '含候车估算', '取行李与寄存', '若铁路中断，请住宿协助确认正规出租。'),
             ('河岸小院', '河岸美术馆', '步行', '15–20', '20', '13:40', '估算', '入口排队', '大件行李留在住宿；预约入口待核。')]),
    dict(date='6月13日', week='周日', city='青湾 · 手工艺与音乐', hotel='河岸小院 Riverside House',
         stay='已订（虚构测试状态）', night='2', stay_note='连续入住，无需换酒店；早餐是否包含待核。',
         route=['河岸小院', '旧城工艺馆', '松庭音乐厅'],
         logic='上午集中看工艺，午后回住宿休息；晚间以音乐会为锚点，至少提前30分钟到场。',
         anchor='松庭音乐会', anchor_time='19:30开始、19:00报到均为虚构测试时间；固定安排不代表已订。',
         events=[
             dict(time='10:00–12:00', title='旧城工艺馆与玻璃工作室', icon='art', state='已选／未订',
                  intro='先看木模、玻璃坯与成品的连续展示，再观察工匠如何控制器壁厚度。重点比较同一器形的手工痕迹，理解日用器物如何兼顾美感与耐用。',
                  execution='演示暂按11:00规划，实际场次待公布；12:15–13:15午餐，14:00–16:00回住宿休息。',
                  highlight='看器底、口沿与接缝，比单看成品陈列更容易理解制作过程。',
                  warning='热加工区是否开放待核；如无演示，以常设展为主，不保证现场制作。'),
             dict(time='19:00–21:15', title='松庭音乐厅 · 室内乐之夜', icon='ticket', state='未开放预订',
                  intro='建议关注弦乐声部之间的问答，并在慢乐章留意中提琴如何承接主题。音乐厅尺度较小，选择视线无遮挡的位置比追求最前排更实用。',
                  execution='16:45–17:45提前晚餐，17:45离餐；19:00前完成寄存与找座，19:30开演。节目、票价与散场时间均待公布。',
                  highlight='演前保留安静休息时间，节目单公布后再补充作品导听。',
                  warning='不得将规划开演时间标为官方时刻；若演出不成立，保留晚餐并取消夜间赶场。')],
         backup='若音乐会未开放或取消，改在旧城晚餐后回住宿；不临时添加跨区活动。',
         transfers=[
             ('河岸小院', '旧城工艺馆', '步行', '20–25', '10', '09:50', '估算', '入口确认', '雨天可选择出租，费用待查。'),
             ('晚餐地点', '松庭音乐厅', '公共交通＋步行', '20–35', '30', '19:00', '估算', '寄存与找座', '实际开演时间公布后，重新核对最晚离餐时间。'),
             ('松庭音乐厅', '河岸小院', '出租', '15–25', '10', '22:00', '估算目标', '散场候车', '不要把候车时间当作保证。')]),
    dict(date='6月14日', week='周一', city='青湾 → 山城 · 换乘与离开', hotel='河岸小院 Riverside House',
         stay='退房日', night='2', stay_note='07:45退房；全程随身带行李，不安排回酒店取件。',
         route=['青湾中央站', '山城历史档案馆', '山城机场'],
         logic='先完成城际换乘，再用车站附近的短参观衔接返程；保留机场缓冲，参观服从当天实际到达时间。',
         anchor='返程与机场到场', anchor_time='19:00起飞仅为虚构样例；目标16:00到值机区，航班票面待核。',
         events=[
             dict(time='07:45–11:30', title='退房与跨城列车', icon='train', state='规划样例／未订',
                  intro='将换乘集中在上午，进站前准备车票与身份证件。山城到站后先确认行李寄存，再决定是否进入档案馆。',
                  execution='列车09:10→10:40仅为规划样例；车站换乘预留25–35分钟。11:30–12:30午餐。',
                  highlight='把行李处理放在参观之前，避免临近机场行程时折返。',
                  warning='若11:30后仍未完成寄存，取消档案馆；寄存服务与关门时间待核。'),
             dict(time='12:45–13:40', title='山城历史档案馆 Archivio della Città e delle Memorie del Fiume', icon='art', state='备选／开放待核',
                  intro='沿旧地图、商船记录与居民口述的顺序阅读展览，比较城市如何随河道改变。重点看同一街区在两张地图上的位置差异，理解港口与生活空间的关系。',
                  execution='仅在周一开放且可寄存行李时执行；13:40必须离馆，取件后去机场，16:00前到值机区。',
                  highlight='以地图对读为核心，现场最多停留55分钟。',
                  warning='这是可删减项目；不因门票已买而挤占机场缓冲。')],
         backup='若城际列车晚点、寄存不可用或档案馆闭馆，直接午餐后前往机场；不增加另一处景点。',
         transfers=[
             ('河岸小院', '青湾中央站', '出租', '20–30', '25', '08:45', '估算', '进站与找站台', '07:45退房离店；若道路受阻，优先保障列车。'),
             ('青湾中央站', '山城中央站', '城际列车', '90', '25–35', '11:15', '规划样例', '换站台与寄存', '09:10→10:40待实际时刻公布；不得作为已购车次。'),
             ('山城历史档案馆', '车站寄存处', '步行', '10–15', '20', '14:15', '估算', '取行李', '13:40离馆；寄存处若排队，不再追加活动。'),
             ('山城中央站', '山城机场航站楼', '机场快线＋步行', '45–60', '20–30', '16:00', '估算', '候车与航站楼步行', '铁路中断则确认正规出租；道路耗时和报价当日核实。')]),
]


def fill(text, values):
    """Unknown tokens fail instead of silently discarding planning material."""
    def value(match):
        key = match[1]
        if key not in values:
            raise ValueError('Unfilled template token: ' + key)
        return escape(str(values[key]), quote=True)
    return re.sub(r'\{\{(.*?)\}\}', value, text)


def render(template=TEMPLATE):
    raw = Path(template).read_text(encoding='utf-8')
    begin = '<!-- REPEAT 逐日卡片 day1..dayN -->'
    end = '<!-- /REPEAT 逐日卡片 -->'
    before, rest = raw.split(begin, 1)
    day_template, after = rest.split(end, 1)
    # Keep candidate counts, trip days and hotel-night numbers independent.
    day_template = day_template.replace('第 {{N}} 晚', '第 {{STAY_NIGHT}} 晚').replace('{{N}}选一', '{{CANDIDATE_COUNT}} 项候选')
    # No fabricated geographical precision: remove the example map geometry.
    day_template = day_template.split('<div class="map">', 1)[0] + '</div></section>'
    event_template = re.search(r'<div class="event">.*?</div></div>', day_template, re.S)[0]
    transfer_template = re.search(r'<!-- REPEAT 交通段.*?-->(.*?)<!-- /REPEAT -->', day_template, re.S)[1]
    common = {
        'TRIP_TITLE':'青湾与山城 · 三日模板示例', '主':'1', '次':'0', 'DESTINATION_EN':'FICTIONAL JOURNEY',
        '一句话描述：天数、同行、主题；已订住宿等关键状态':INTRO,
        'DATE_RANGE_EN 如 16—19 OCT 2026':'12—14 JUN 2027', 'N':'3', 'M':'2', 'STAGE 如 WORKING DRAFT':'虚构测试',
        '本组目标：稀缺资格／硬交通':'先确认交通与演出', '唯一KEY':'concert', '对象':'松庭音乐会', '动作':'确认节目与预约',
        'PHONE':'000', '问题1':'是否有目标日期场次', '问题2':'寄存规则', '问题3':'退改条件', 'URL':'https://example.com/fixture',
        '购票入口名':'示例入口（不可预订）', '来源与查阅日期':'虚构测试材料，无实际查询', '未预约／未购票／已订':'未开放预订',
        '如：航班、入住、餐饮':'住宿与行李', 'KEY':'fixture', '你提供…尚未核对票面；需补齐…':'确认住宿晚到、寄存和早餐条件',
        '…':'待核实', '待讨论的弹性项':'天气与体力', '按天气/体力决定…':'若下雨，取消雕塑步道，保留休息', '待定':'待定',
        '哪些已订、哪些由用户提供尚未核对订单':'以下状态均为虚构测试；并无真实订单',
        'M/D':'6/12', '短标签':'抵达', '类别':'交通', '名称/编号':'机场接驳', '已订／票面待核／代约':'规划样例／未订',
        '时间、地址、来源层级；被替换的旧信息写“旧…不可沿用”':'09:20抵达为虚构样例，票面与目标日期均待核。',
        '预算范围、币种、估算依据与查阅日期':'虚构两人预算，仅检验金额与条件的显示', '费用项目':'城际交通',
        '币种与金额或待查':'EUR 120–160（两人估算）', '已付／估算；包含与不包含项':'未支付；含列车，不含出租与行李寄存',
        'YYYY/MM/DD':'2027/01/01', '本版改动':'虚构示例，无实际旅行建议',
        '仍为草案的部分；未订项目；需按旅行日期复核的内容':'地点、订单、时间与价格均为测试材料；不可预订或导航。',
        'TRIP_KEY':'fictional-delivery-fixture',
    }
    # Each priority entry has its own stable local checkbox key.
    before = before.replace('data-check="{{KEY}}"', 'data-check="stay"', 1).replace('data-check="{{KEY}}"', 'data-check="weather"', 1)
    before = before.replace('data-check="stay"><span><b>{{对象}}｜{{动作}}</b>', 'data-check="stay"><span><b>河岸小院｜确认入住与行李</b>')
    before = before.replace('data-check="weather"><span><b>{{对象}}｜{{动作}}</b>', 'data-check="weather"><span><b>雕塑步道｜按天气决定</b>')
    nav = ''.join(f'<a href="#day{i}">6/{11+i} · D0{i}</a>' for i in range(1, 4))
    before = re.sub(r'<!-- REPEAT 每天一个 -->.*?<!-- /REPEAT -->', nav, before, flags=re.S)
    anchor_template = re.search(r'<div class="anchor-card" id="anchor-.*?</div>', before, re.S)[0]
    anchors = ''.join(fill(anchor_template, dict(common, KEY=f'day{i}', **{'M/D':f'6/{11+i}', '名称/编号':day['anchor'],
                   '时间、地址、来源层级；被替换的旧信息写“旧…不可沿用”':day['anchor_time']})) for i,day in enumerate(DAYS,1))
    before = before.replace(anchor_template, anchors)
    # The demonstration contains no working telephone number.
    before = before.replace('<a href="tel:{{PHONE}}">{{PHONE}}</a>', '示例票务窗口（无真实电话）')
    days = []
    for i, day in enumerate(DAYS, 1):
        events = []
        for event in day['events']:
            values = dict(common, **{'HH:MM–HH:MM':event['time'], '项目':event['title'], '票面待核／未订':event['state'],
                '介绍：为什么值得去、现场看什么、参观顺序；按项目价值分配篇幅':event['intro'],
                '执行：停留、入口、预约到场、必要条件':event['execution'], '核心细节或体验提示':event['highlight'],
                '硬截止、限制及未满足条件的处理':event['warning'], '来源链接 · YYYY/MM/DD 查阅':'依据：虚构测试材料；没有实际核实结果。',
                '说明：停留、门到门、触发规则':event['intro']+event['execution']})
            block = event_template.replace('href="#icon-art"', f'href="#icon-{event["icon"]}"', 1)
            # Previous template had no callout slots: retain exactly the same input facts.
            if '{{核心细节或体验提示}}' not in block:
                block = block.replace('</div></div>', '<p>{{核心细节或体验提示}}</p><p>{{硬截止、限制及未满足条件的处理}}</p></div></div>')
            block = fill(re.sub(r'<!--.*?-->', '', block, flags=re.S), values)
            events.append(block)
        daily = re.sub(r'<div class="timeline">.*?<!-- /REPEAT -->\s*</div>', '<div class="timeline">'+''.join(events)+'</div>', day_template, count=1, flags=re.S)
        transfers = []
        for start, finish, mode, duration, buffer, clock, basis, cause, condition in day['transfers']:
            values = {'起点':start,'终点':finish,'方式':mode,'X–Y':duration,'估算／公开时刻／司机待核':basis,
                      '缓冲原因':cause,'缓冲分钟':buffer,'报到钟点':clock,'必要条件与失败备选':condition,
                      '到场动作：抵达入口／完成报到／完成取件':{
                          '取行李':'完成取件', '寄存与找座':'完成寄存与找座', '进站与找站台':'到站台',
                          '换站台与寄存':'完成寄存', '取行李与寄存':'完成寄存', '入口排队':'到指定入口',
                          '入口确认':'到入口', '散场候车':'回住宿', '候车与航站楼步行':'到值机区'}[cause]}
            block = transfer_template
            if '{{必要条件与失败备选}}' not in block:
                block = block.replace('</li>', '；{{缓冲原因}}另留{{缓冲分钟}}分钟，目标{{报到钟点}}前到场。{{必要条件与失败备选}}</li>')
            if '步行' == mode:
                block = block.replace('#icon-train','#icon-walk')
            elif '列车' not in mode and '快线' not in mode:
                block = re.sub(r'<svg class="icon".*?</svg>', '', block)
            transfers.append(fill(block, values))
        daily = re.sub(r'<!-- REPEAT 交通段.*?-->.*?<!-- /REPEAT -->', ''.join(transfers), daily, flags=re.S)
        if '{{若何时发生什么，则替换或删减什么；保留后续硬约束}}' not in daily:
            daily = daily.replace('<!-- 可选：候选比较块 -->', '<p class="day-intro">{{若何时发生什么，则替换或删减什么；保留后续硬约束}}</p><!-- 可选：候选比较块 -->')
        values = dict(common, **{'01':f'{i:02}', 'M月D日':day['date'], '周X':day['week'], '城市 · 当日主题':day['city'],
            'A':day['route'][0], 'B':day['route'][1], 'C':day['route'][2], '酒店':day['hotel'], 'STAY_NIGHT':day['night'], 'CANDIDATE_COUNT':'1',
            '如：跨午夜次日凌晨到店 · 晚到保房待确认':day['stay_note'], '已订／未订／退房日':day['stay'],
            'KEY':f'day{i}', '名称 · 状态':day['anchor']+' · 规划样例',
            '当日逻辑：从最后硬约束倒排；触发规则“若X则Y”，如“T 前必须发车，否则改吃备餐”':day['logic'],
            '若何时发生什么，则替换或删减什么；保留后续硬约束':day['backup'], '问题列表':'开放时间、寄存条件、当日体力',
            'M/D':f'6/{11+i}', '类别':'同区备用体验', '序号':'1', '名称':'桥边阅读室', '一句定位：动线优先／就近备选…':'雨天就近备选',
            '地址':'虚构桥边街12号', '同名/近名区分；单条负评注“未独立核实”':'无真实评价依据；未选未订。', '来源':'虚构来源标记'})
        daily = fill(re.sub(r'<!--.*?-->', '', daily, flags=re.S), values).replace('id="day1"',f'id="day{i}"',1)
        if i==2:
            daily=daily.replace('class="stay-status status is-pending"','class="stay-status status is-booked"')
        days.append(daily)
    after = re.sub(r'<details class="sources" id="map-sources">.*?</details>', '<details class="sources" id="map-sources"><summary>示例依据与精度说明</summary><p id="fixture-source">全部地点、时间、金额和预订状态均为虚构，仅用于交付验收；没有绘制地图，不可导航。</p></details>',after,flags=re.S)
    if 'class="budget"' not in after:
        after='<section class="budget" id="budget"><p>'+common['币种与金额或待查']+'；'+common['已付／估算；包含与不包含项']+'</p></section>'+after
    return fill(re.sub(r'<!--.*?-->', '', before, flags=re.S), common)+''.join(days)+fill(re.sub(r'<!--.*?-->', '', after, flags=re.S), common)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template',type=Path,default=TEMPLATE)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(render(args.template),encoding='utf-8')
    print(args.output)
