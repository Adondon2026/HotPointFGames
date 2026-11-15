// Single visual catalog for the room settings, standalone lobby and battlefield.
const siegeCatalog={
  "bounce": {
    "group": "弹道",
    "color": "#80d2e5",
    "label": "弹跳弹",
    "path": "M3 16L8 7 15 16 21 5 M17 5H21V9"
  },
  "through": {
    "group": "弹道",
    "color": "#80d2e5",
    "label": "穿透弹",
    "path": "M3 12H21 M16 7L21 12 16 17 M9 4V20 M12 4V20"
  },
  "splitshot": {
    "group": "弹道",
    "color": "#80d2e5",
    "label": "分裂效果",
    "path": "M12 21V12L5 5 M12 12L19 5 M5 10V5H10 M14 5H19V10"
  },
  "spiral": {
    "group": "弹道",
    "color": "#80d2e5",
    "label": "螺旋弹",
    "path": "M12 12C9 9 15 6 17 11S12 20 6 15 3 5 12 3 23 10 20 17"
  },
  "repeat": {
    "group": "弹道",
    "color": "#80d2e5",
    "label": "连发弹",
    "path": "M4 6H11L14 9 11 12H4Z M10 14H17L20 17 17 20H10Z"
  },
  "downpour": {
    "group": "弹道",
    "color": "#80d2e5",
    "label": "向下投弹",
    "path": "M3 5H21 M6 9V18 M3 15L6 18 9 15 M17 9V18 M14 15L17 18 20 15"
  },
  "larpa": {
    "group": "弹道",
    "color": "#80d2e5",
    "label": "反弹复制",
    "path": "M3 16L9 5 15 15 M9 5L21 8 M16 4L21 8 17 12 M12 17L15 15 17 19"
  },
  "snake": {
    "group": "弹道",
    "color": "#80d2e5",
    "label": "蛇形弹",
    "path": "M3 16C7 1 9 23 13 9S19 20 21 5"
  },
  "dive": {
    "group": "飞行操纵",
    "color": "#80d2e5",
    "label": "俯冲操纵",
    "path": "M3 4Q17 4 17 20 M12 15L17 20 22 15"
  },
  "antigrav": {
    "group": "飞行操纵",
    "color": "#80d2e5",
    "label": "反重力操纵",
    "path": "M5 17V7 M2 10L5 7 8 10 M12 20V3 M9 6L12 3 15 6 M19 17V7 M16 10L19 7 22 10"
  },
  "homing": {
    "group": "弹道",
    "color": "#80d2e5",
    "label": "近距追踪",
    "path": "M12 3V8 M12 16V21 M3 12H8 M16 12H21 M12 8A4 4 0 1 0 12 16A4 4 0 1 0 12 8"
  },
  "pingpong": {
    "group": "飞行操纵",
    "color": "#80d2e5",
    "label": "折返操纵",
    "path": "M4 6H20L4 18H20 M16 14L20 18 16 22"
  },
  "big": {
    "group": "火力",
    "color": "#edaf67",
    "label": "巨型弹",
    "path": "M12 3A9 9 0 1 0 12 21A9 9 0 1 0 12 3 M12 8A4 4 0 1 0 12 16A4 4 0 1 0 12 8"
  },
  "power": {
    "group": "火力",
    "color": "#edaf67",
    "label": "强力弹",
    "path": "M13 2L5 13H11L10 22 20 10H13Z"
  },
  "pierce": {
    "group": "火力",
    "color": "#edaf67",
    "label": "破甲弹",
    "path": "M3 17L20 4 16 15 12 12 M6 3L8 8 5 12 9 17 8 21"
  },
  "shock": {
    "group": "火力",
    "color": "#edaf67",
    "label": "冲击波",
    "path": "M4 7Q10 12 4 17 M9 4Q19 12 9 20 M15 2Q27 12 15 22"
  },
  "push": {
    "group": "火力",
    "color": "#edaf67",
    "label": "推进弹",
    "path": "M3 6L10 12 3 18 M10 6L17 12 10 18 M17 6L23 12 17 18"
  },
  "bounceblast": {
    "group": "火力",
    "color": "#edaf67",
    "label": "爆破效果",
    "path": "M3 18L10 7 17 18 M10 2V5 M5 4L7 6 M15 4L13 6 M19 8H22 M17 11L20 14"
  },
  "blackhole": {
    "group": "特效",
    "color": "#cfafea",
    "label": "黑洞效果",
    "path": "M12 5A7 7 0 1 0 12 19A7 7 0 1 0 12 5 M3 15Q1 7 12 5 M21 9Q23 17 12 19 M12 10A2 2 0 1 0 12 14A2 2 0 1 0 12 10"
  },
  "fuse": {
    "group": "特效",
    "color": "#cfafea",
    "label": "定时引信",
    "path": "M12 5A8 8 0 1 0 12 21A8 8 0 1 0 12 5 M12 8V13L16 15 M9 2H15"
  },
  "ignite": {
    "group": "特效",
    "color": "#cfafea",
    "label": "点火效果",
    "path": "M12 2C15 8 21 10 19 16C17 23 5 22 5 15C5 10 10 8 12 2Z M12 12L9 17 12 20 15 17Z"
  },
  "firetrail": {
    "group": "特效",
    "color": "#cfafea",
    "label": "燃烧拖尾",
    "path": "M3 17H10 M2 12H7 M6 7H11 M16 3Q24 14 19 19Q12 23 11 16Q11 11 16 3Z"
  },
  "firearc": {
    "group": "特效",
    "color": "#cfafea",
    "label": "火焰连线",
    "path": "M3 5A3 3 0 1 0 3 11A3 3 0 1 0 3 5 M21 13A3 3 0 1 0 21 19A3 3 0 1 0 21 13 M6 8L10 14 12 9 16 16 18 16"
  },
  "shotshield": {
    "group": "特效",
    "color": "#cfafea",
    "label": "弹体护盾",
    "path": "M12 3L20 6V12Q19 18 12 21Q5 18 4 12V6Z M9 12A3 3 0 1 0 15 12A3 3 0 1 0 9 12"
  },
  "mine": {
    "group": "特效",
    "color": "#cfafea",
    "label": "地雷效果",
    "path": "M4 17H20L17 10H7Z M8 10V7H16V10 M12 2V5 M3 5L6 7 M21 5L18 7"
  },
  "shield": {
    "group": "防御与建造",
    "color": "#a5cf9a",
    "label": "护盾",
    "path": "M12 3L20 6V12Q19 18 12 21Q5 18 4 12V6Z M8 12L11 15 16 9"
  },
  "armor": {
    "group": "防御与建造",
    "color": "#a5cf9a",
    "label": "加固",
    "path": "M4 4H20V20H4Z M4 4L20 20 M20 4L4 20 M9 9H15V15H9Z"
  },
  "buffer": {
    "group": "防御与建造",
    "color": "#a5cf9a",
    "label": "缓冲层",
    "path": "M4 5H20 M4 19H20 M6 5L18 8 6 12 18 16 6 19"
  },
  "heal": {
    "group": "防御与建造",
    "color": "#a5cf9a",
    "label": "修复",
    "path": "M9 3H15V9H21V15H15V21H9V15H3V9H9Z"
  },
  "wooddrop": {
    "group": "防御与建造",
    "color": "#a5cf9a",
    "label": "木块生成",
    "path": "M4 4H20V20H4Z M4 10H20 M4 15H20 M10 4V10 M15 10V15 M9 15V20"
  },
  "stonedrop": {
    "group": "防御与建造",
    "color": "#a5cf9a",
    "label": "石块生成",
    "path": "M3 20V12L7 6 16 4 21 11V20Z M3 12L11 14 16 4 M11 14V20 M11 14L21 11"
  },
  "gunteleport": {
    "group": "空间",
    "color": "#8cabea",
    "label": "炮台瞬移",
    "path": "M3 19H12V15H3Z M6 15L12 8 16 11 10 15 M15 3H21V9 M21 3L15 9"
  },
  "coreteleport": {
    "group": "空间",
    "color": "#8cabea",
    "label": "核心瞬移",
    "path": "M9 5L16 12 9 19 2 12Z M14 5H21V12 M21 5L16 10"
  },
  "clone": {
    "group": "空间",
    "color": "#8cabea",
    "label": "克隆增益",
    "path": "M3 13H14V21H3Z M7 13L13 7 16 10 12 13 M10 3H21V11 M17 3V7H21"
  },
  "heavy": {
    "group": "负面",
    "color": "#b4b7bc",
    "label": "重重子弹",
    "path": "M3 12H21L18 21H6Z M12 2V10 M8 6L12 10 16 6"
  },
  "vanish": {
    "group": "负面",
    "color": "#b4b7bc",
    "label": "湮灭子弹",
    "path": "M12 3A9 9 0 0 0 3 12 M3 15L5 18 M8 20L11 21 M15 20L18 18 M20 15L21 12 M20 8L18 5 M9 9L15 15 M15 9L9 15"
  },
  "wobble": {
    "group": "负面",
    "color": "#b4b7bc",
    "label": "不稳定子弹",
    "path": "M3 18L8 5 12 16 16 4 21 13 M18 11L21 13 22 9"
  },
  "fart": {
    "group": "负面",
    "color": "#b4b7bc",
    "label": "屁屁子弹",
    "path": "M5 15Q1 12 5 9Q4 3 10 5Q15 1 18 7Q25 8 20 14Q23 20 15 19H6 M3 20H9"
  }
};
const siegeIcon=(k,size=22)=>{const i=siegeCatalog[k];return i?'<svg class="siege-item-icon" aria-hidden="true" width="'+size+'" height="'+size+'" viewBox="0 0 24 24" style="color:'+i.color+';vertical-align:middle;flex-shrink:0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="'+i.path+'"/></svg>':''};

const siegeActiveKeys=Object.keys(siegeCatalog).filter(k=>!['larpa','downpour','fuse'].includes(k));

const siegeV24Keys=['splitshot','repeat','bounce','through','homing','shield','armor','heal','wooddrop','stonedrop','coreteleport','gunteleport','blackhole','bounceblast','pierce','big','push','heavy','vanish','wobble','fart'];
const siegeV24Skills=['shield','armor','heal','coreteleport','gunteleport'];
const siegeV24Negatives=['heavy','vanish','wobble','fart'];
const siegeV24Cap=k=>['splitshot','repeat','shield'].includes(k)?3:['homing','heal','coreteleport','gunteleport'].includes(k)?1:5;
const siegeRarity=k=>['homing','heal','coreteleport','gunteleport'].includes(k)?'precious':['repeat','blackhole','shield'].includes(k)?'rare':['splitshot','through','bounceblast','pierce','armor'].includes(k)?'uncommon':'common';
const siegeV24Names={splitshot:'分裂弹',repeat:'连发',bounce:'弹跳效果',through:'穿透效果',homing:'制导效果',shield:'核心护盾',armor:'防御加固',heal:'核心修复',wooddrop:'木块生成',stonedrop:'石块生成',coreteleport:'核心瞬移',gunteleport:'炮台瞬移',blackhole:'黑洞效果',bounceblast:'爆炸效果',pierce:'破甲效果',big:'增大效果',push:'推进效果',heavy:'重重效果',vanish:'湮灭效果',wobble:'不稳定效果',fart:'屁屁效果'};
const siegeV24Group=k=>siegeV24Skills.includes(k)?'技能':siegeV24Negatives.includes(k)?'负面':k==='splitshot'?'弹药':k==='repeat'?'机制':'效果';
