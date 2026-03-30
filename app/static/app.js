const tooltip = d3.select('#tooltip');

const API_BASE = window.location.origin;
const STATIC_DASHBOARD_SNAPSHOT_PATH = '/static/dashboard_snapshot.json';

const CRIME_TYPE_ZH_MAP = {
  THEFT: '盗窃',
  BATTERY: '人身伤害',
  'CRIMINAL DAMAGE': '刑事毁坏',
  ASSAULT: '袭击（未遂/威胁）',
  NARCOTICS: '毒品相关',
  BURGLARY: '入室盗窃',
  ROBBERY: '抢劫',
  HOMICIDE: '凶杀',
  'MOTOR VEHICLE THEFT': '机动车盗窃',
  'DECEPTIVE PRACTICE': '欺诈',
  'CRIMINAL TRESPASS': '刑事非法侵入',
  'WEAPONS VIOLATION': '武器违法',
  'CONCEALED CARRY LICENSE VIOLATION': '隐蔽持枪许可证违规',
  PROSTITUTION: '卖淫相关',
  'OFFENSE INVOLVING CHILDREN': '侵害儿童相关犯罪',
  'SEX OFFENSE': '性犯罪（其他）',
  'CRIMINAL SEXUAL ASSAULT': '刑事性侵',
  ARSON: '纵火',
  KIDNAPPING: '绑架',
  STALKING: '跟踪',
  INTIMIDATION: '恐吓',
  'INTERFERENCE WITH PUBLIC OFFICER': '妨碍公务',
  GAMBLING: '赌博',
  'PUBLIC PEACE VIOLATION': '扰乱公共秩序',
  'LIQUOR LAW VIOLATION': '酒类法规违法',
  OBSCENITY: '淫秽行为',
  'PUBLIC INDECENCY': '公共猥亵',
  'OTHER OFFENSE': '其他犯罪',
  'OTHER NARCOTIC VIOLATION': '其他毒品违法',
  'HUMAN TRAFFICKING': '人口贩运',
  'NON-CRIMINAL': '非刑事事件',
  'NON-CRIMINAL (SUBJECT SPECIFIED)': '非刑事事件（对象明确）',
  RITUALISM: '仪式相关违法',
  'CRIM SEXUAL ASSAULT': '刑事性侵（旧分类）',
};

const CRIME_TYPE_ALIAS_MAP = {
  'OTHER OFFENCE': 'OTHER OFFENSE',
  'NON CRIMINAL': 'NON-CRIMINAL',
  'NON-CRIMINAL (SUBJECT SPECIFED)': 'NON-CRIMINAL (SUBJECT SPECIFIED)',
};

const WEEKDAY_ZH_MAP = {
  MON: '周一',
  TUE: '周二',
  WED: '周三',
  THU: '周四',
  FRI: '周五',
  SAT: '周六',
  SUN: '周日',
  1: '周一',
  2: '周二',
  3: '周三',
  4: '周四',
  5: '周五',
  6: '周六',
  7: '周日',
};

const CONCLUSION_TITLE_ZH_MAP = {
  'Dataset scale': '数据规模',
  'Peak annual crime': '年度峰值',
  'Lowest annual crime': '年度低点',
  'Peak weekday': '高发星期',
  'Peak hour': '高发时段',
  'Top crime type': '高发类型',
  'Top district': '高发警区',
  'Top community area': '高发社区',
  'Arrest rate change': '逮捕率变化',
  'Arrest rate level': '逮捕率水平',
  'Domestic incident burden': '家庭相关事件占比',
  'Peak month': '高发月份',
  'Highest-risk block': '高风险街区',
};

const CONCLUSION_TEXT_ZH_MAP = {
  'No annual data available.': '暂无年度数据。',
  'No weekday distribution data available.': '暂无周内分布数据。',
  'No hourly distribution data available.': '暂无小时分布数据。',
  'No crime-type share data available.': '暂无犯罪类型占比数据。',
  'No district comparison data available.': '暂无警区对比数据。',
  'No community-area comparison data available.': '暂无社区对比数据。',
  'No arrest trend data available.': '暂无逮捕率趋势数据。',
  'No domestic trend data available.': '暂无家庭相关事件趋势数据。',
};

const els = {
  form: document.getElementById('filters'),
  resetBtn: document.getElementById('reset-btn'),
  startYear: document.getElementById('start-year'),
  endYear: document.getElementById('end-year'),
  crimeType: document.getElementById('crime-type'),
  crimeTypeDropdown: document.getElementById('crime-type-dropdown'),
  crimeTypeTrigger: document.getElementById('crime-type-trigger'),
  crimeTypeMenu: document.getElementById('crime-type-menu'),
  topN: document.getElementById('top-n'),
  statusText: document.getElementById('status-text'),
  healthIndicator: document.getElementById('health-indicator'),
  kpiTotal: document.getElementById('kpi-total'),
  kpiRange: document.getElementById('kpi-range'),
  kpiTypes: document.getElementById('kpi-types'),
  kpiMissing: document.getElementById('kpi-missing'),
  insightAnnual: document.getElementById('insight-annual'),
  insightWeekly: document.getElementById('insight-weekly'),
  insightHourly: document.getElementById('insight-hourly'),
  insightType: document.getElementById('insight-type'),
  insightDistrict: document.getElementById('insight-district'),
  insightHeatmap: document.getElementById('insight-heatmap'),
  insightYoy: document.getElementById('insight-yoy'),
  conclusionList: document.getElementById('conclusion-list'),
};

const defaults = {
  startYear: '',
  endYear: '',
  crimeTypes: [],
  topN: 10,
};

let currentData = null;
let currentFilters = null;
const crimeTypeState = {
  selectedAll: true,
  selectedValues: new Set(),
  options: [],
};

function ensureCrimeTypeDropdownElements() {
  if (els.crimeTypeDropdown && els.crimeTypeTrigger && els.crimeTypeMenu) {
    return;
  }

  if (!els.crimeType) {
    return;
  }

  const host = els.crimeType.closest('label') || els.crimeType.parentElement;
  if (!host) {
    return;
  }

  let dropdown = host.querySelector('#crime-type-dropdown');
  if (!dropdown) {
    dropdown = document.createElement('div');
    dropdown.id = 'crime-type-dropdown';
    dropdown.className = 'multi-select';
  }

  let trigger = host.querySelector('#crime-type-trigger');
  if (!trigger) {
    trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.id = 'crime-type-trigger';
    trigger.className = 'multi-select-trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.textContent = '全部类型（已勾选）';
    dropdown.appendChild(trigger);
  }

  let menu = host.querySelector('#crime-type-menu');
  if (!menu) {
    menu = document.createElement('div');
    menu.id = 'crime-type-menu';
    menu.className = 'multi-select-menu';
    menu.setAttribute('role', 'listbox');
    menu.setAttribute('aria-multiselectable', 'true');
    menu.hidden = true;
    dropdown.appendChild(menu);
  }

  if (!dropdown.parentElement) {
    host.insertBefore(dropdown, els.crimeType);
  }

  els.crimeType.classList.add('native-multi-select');
  els.crimeType.setAttribute('hidden', 'hidden');
  els.crimeType.setAttribute('aria-hidden', 'true');
  els.crimeType.setAttribute('tabindex', '-1');

  els.crimeTypeDropdown = dropdown;
  els.crimeTypeTrigger = trigger;
  els.crimeTypeMenu = menu;
}

function toInt(value, fallback = null) {
  if (value === '' || value === null || value === undefined) {
    return fallback;
  }
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '--';
  }
  return Number(value).toLocaleString('zh-CN');
}

function formatCompactCount(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return '--';
  }
  if (Math.abs(numeric) >= 10000) {
    const inWan = numeric / 10000;
    const rounded = Math.abs(inWan) >= 100 ? Math.round(inWan) : Math.round(inWan * 10) / 10;
    return `${rounded.toLocaleString('zh-CN')}万`;
  }
  return formatNumber(numeric);
}

function normalizeCrimeType(rawType) {
  return String(rawType || '')
    .trim()
    .toUpperCase()
    .replace(/\s*-\s*/g, '-')
    .replace(/\s+/g, ' ');
}

function translateCrimeType(rawType) {
  const key = normalizeCrimeType(rawType);
  const canonicalKey = CRIME_TYPE_ALIAS_MAP[key] || key;
  if (!key) {
    return '未知类型';
  }
  return CRIME_TYPE_ZH_MAP[canonicalKey] || canonicalKey;
}

function disambiguateDuplicateCrimeLabels(options) {
  const labelCount = new Map();
  options.forEach((item) => {
    labelCount.set(item.label, (labelCount.get(item.label) || 0) + 1);
  });

  return options.map((item) => {
    if ((labelCount.get(item.label) || 0) <= 1) {
      return item;
    }
    return {
      ...item,
      label: `${item.label}（${item.value}）`,
    };
  });
}

function translateWeekday(value) {
  if (value === null || value === undefined || value === '') {
    return '未知';
  }

  const numeric = Number(value);
  if (Number.isFinite(numeric) && WEEKDAY_ZH_MAP[numeric]) {
    return WEEKDAY_ZH_MAP[numeric];
  }

  const upper = String(value).trim().toUpperCase();
  return WEEKDAY_ZH_MAP[upper] || String(value);
}

function translateConclusionTitle(title) {
  return CONCLUSION_TITLE_ZH_MAP[title] || title;
}

function translateConclusionText(text) {
  if (!text) {
    return '';
  }

  if (CONCLUSION_TEXT_ZH_MAP[text]) {
    return CONCLUSION_TEXT_ZH_MAP[text];
  }

  const patterns = [
    {
      regex: /^Within selected range, total records are ([\d,]+) from (\d{4}) to (\d{4})\.$/i,
      format: (m) => `在当前筛选范围内，共有 ${m[1]} 条记录，时间覆盖 ${m[2]} 年至 ${m[3]} 年。`,
    },
    {
      regex: /^Peak annual volume is in (\d{4}) with ([\d,]+) cases\.$/i,
      format: (m) => `年度峰值出现在 ${m[1]} 年，共 ${m[2]} 起案件。`,
    },
    {
      regex: /^Lowest annual volume is in (\d{4}) with ([\d,]+) cases\.$/i,
      format: (m) => `年度低点出现在 ${m[1]} 年，共 ${m[2]} 起案件。`,
    },
    {
      regex: /^Weekday ([A-Za-z]+) is the highest-crime day with ([\d,]+) cases\.$/i,
      format: (m) => `${translateWeekday(m[1])}是案件量最高的一天，共 ${m[2]} 起。`,
    },
    {
      regex: /^Hour (\d{1,2}) is the peak crime hour with ([\d,]+) cases\.$/i,
      format: (m) => `${m[1]} 时是高发时段，共 ${m[2]} 起案件。`,
    },
    {
      regex: /^Top crime type is (.+) with ([\d,]+) cases \(([\d.]+)%\)\.$/i,
      format: (m) => `高发类型为${translateCrimeType(m[1])}，共 ${m[2]} 起，占比 ${m[3]}%。`,
    },
    {
      regex: /^District (\d+) ranks first with ([\d,]+) cases\.$/i,
      format: (m) => `警区 ${m[1]} 排名第一，共 ${m[2]} 起案件。`,
    },
    {
      regex: /^Community area (\d+) ranks first with ([\d,]+) cases\.$/i,
      format: (m) => `社区 ${m[1]} 排名第一，共 ${m[2]} 起案件。`,
    },
    {
      regex: /^Arrest rate changed from ([\d.]+)% in (\d{4}) to ([\d.]+)% in (\d{4})\.$/i,
      format: (m) => `逮捕率从 ${m[2]} 年的 ${m[1]}% 变化到 ${m[4]} 年的 ${m[3]}%。`,
    },
    {
      regex: /^Arrest rate in (\d{4}) is ([\d.]+)%\.$/i,
      format: (m) => `${m[1]} 年逮捕率为 ${m[2]}%。`,
    },
    {
      regex: /^Highest domestic incident rate is ([\d.]+)% in (\d{4})\.$/i,
      format: (m) => `家庭相关事件占比最高年份为 ${m[2]} 年，占比 ${m[1]}%。`,
    },
    {
      regex: /^Month (\d{1,2}) has the highest seasonal volume with ([\d,]+) cases\.$/i,
      format: (m) => `${m[1]} 月案件量最高，共 ${m[2]} 起。`,
    },
    {
      regex: /^Top block is (.+) with ([\d,]+) cases\.$/i,
      format: (m) => `高风险街区为 ${m[1]}，共 ${m[2]} 起案件。`,
    },
  ];

  for (const item of patterns) {
    const match = text.match(item.regex);
    if (match) {
      return item.format(match);
    }
  }

  return text;
}

function setStatus(message, isError = false) {
  els.statusText.textContent = message;
  els.statusText.style.color = isError ? '#8f2d20' : '#2f5a69';
}

function setHealth(statusText, mode) {
  els.healthIndicator.textContent = statusText;
  els.healthIndicator.classList.remove('error', 'success');
  if (mode === 'error') {
    els.healthIndicator.classList.add('error');
  }
  if (mode === 'success') {
    els.healthIndicator.classList.add('success');
  }
}

function setSelectOptions(selectEl, options, allLabel, selectedValue = '') {
  const normalizedSelected = selectedValue === null || selectedValue === undefined ? '' : String(selectedValue).trim();

  const entries = new Map();

  options.forEach((item) => {
    if (!item || item.value === null || item.value === undefined) {
      return;
    }
    const value = String(item.value);
    const label = String(item.label ?? value);
    if (!entries.has(value)) {
      entries.set(value, label);
    }
  });

  selectEl.innerHTML = '';

  const allOption = document.createElement('option');
  allOption.value = '';
  allOption.textContent = allLabel;
  selectEl.appendChild(allOption);

  entries.forEach((label, value) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    selectEl.appendChild(option);
  });

  if (normalizedSelected && !entries.has(normalizedSelected)) {
    const extra = document.createElement('option');
    extra.value = normalizedSelected;
    extra.textContent = normalizedSelected;
    selectEl.appendChild(extra);
  }

  selectEl.value = normalizedSelected;
  if (selectEl.value !== normalizedSelected) {
    selectEl.value = '';
  }
}

function getCrimeTypeSelection() {
  if (crimeTypeState.selectedAll) {
    return [];
  }
  return Array.from(crimeTypeState.selectedValues);
}

function syncCrimeTypeHiddenSelect() {
  const selectedSet = new Set(getCrimeTypeSelection());
  Array.from(els.crimeType.options).forEach((option) => {
    option.selected = selectedSet.has(option.value);
  });
}

function getCrimeTypeLabel(value) {
  const found = crimeTypeState.options.find((item) => item.value === value);
  if (found) {
    return found.label;
  }
  return translateCrimeType(value);
}

function updateCrimeTypeTriggerText() {
  if (!els.crimeTypeTrigger) {
    return;
  }

  if (crimeTypeState.selectedAll) {
    els.crimeTypeTrigger.textContent = '全部类型（已勾选）';
    return;
  }

  const selectedValues = getCrimeTypeSelection();
  if (selectedValues.length === 0) {
    els.crimeTypeTrigger.textContent = '未勾选类型';
    return;
  }

  const labels = selectedValues.map((value) => getCrimeTypeLabel(value));
  if (labels.length <= 2) {
    els.crimeTypeTrigger.textContent = `${labels.join('、')}（已勾选）`;
    return;
  }

  els.crimeTypeTrigger.textContent = `${labels.slice(0, 2).join('、')} 等${labels.length}类（已勾选）`;
}

function renderCrimeTypeMenu() {
  const menu = els.crimeTypeMenu;
  if (!menu) {
    return;
  }
  menu.innerHTML = '';

  const allBtn = document.createElement('div');
  allBtn.className = 'multi-select-option multi-select-option-all';
  allBtn.dataset.value = '__ALL__';
  allBtn.setAttribute('role', 'option');
  allBtn.setAttribute('tabindex', '0');
  allBtn.setAttribute('aria-selected', crimeTypeState.selectedAll ? 'true' : 'false');

  const allLabel = document.createElement('span');
  allLabel.className = 'multi-select-label';
  allLabel.textContent = '全部类型';

  const allCheck = document.createElement('span');
  allCheck.className = 'multi-select-check';
  const allCheckbox = document.createElement('input');
  allCheckbox.type = 'checkbox';
  allCheckbox.className = 'multi-select-checkbox';
  allCheckbox.checked = crimeTypeState.selectedAll;
  allCheckbox.setAttribute('aria-label', '全部类型');
  allCheck.appendChild(allCheckbox);

  allBtn.appendChild(allLabel);
  allBtn.appendChild(allCheck);
  menu.appendChild(allBtn);

  crimeTypeState.options.forEach((item) => {
    const checked = !crimeTypeState.selectedAll && crimeTypeState.selectedValues.has(item.value);
    const btn = document.createElement('div');
    btn.className = 'multi-select-option';
    btn.dataset.value = item.value;
    btn.setAttribute('role', 'option');
    btn.setAttribute('tabindex', '0');
    btn.setAttribute('aria-selected', checked ? 'true' : 'false');

    const label = document.createElement('span');
    label.className = 'multi-select-label';
    label.textContent = item.label;

    const check = document.createElement('span');
    check.className = 'multi-select-check';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'multi-select-checkbox';
    checkbox.checked = checked;
    checkbox.setAttribute('aria-label', item.label);
    check.appendChild(checkbox);

    btn.appendChild(label);
    btn.appendChild(check);
    menu.appendChild(btn);
  });
}

function setCrimeTypeOptions(options, selectedValues = []) {
  const entries = new Map();
  options.forEach((item) => {
    if (!item || item.value === null || item.value === undefined) {
      return;
    }
    const value = String(item.value).trim();
    const label = String(item.label ?? value).trim();
    if (!value || entries.has(value)) {
      return;
    }
    entries.set(value, label || value);
  });

  (Array.isArray(selectedValues) ? selectedValues : []).forEach((item) => {
    const value = String(item || '').trim();
    if (!value || entries.has(value)) {
      return;
    }
    entries.set(value, translateCrimeType(value));
  });

  const mergedOptions = Array.from(entries, ([value, label]) => ({ value, label }));
  crimeTypeState.options = mergedOptions;

  els.crimeType.innerHTML = '';
  mergedOptions.forEach((item) => {
    const option = document.createElement('option');
    option.value = item.value;
    option.textContent = item.label;
    els.crimeType.appendChild(option);
  });

  const selectedSet = new Set(
    (Array.isArray(selectedValues) ? selectedValues : [])
      .map((item) => String(item || '').trim())
      .filter((item) => item),
  );

  if (selectedSet.size === 0) {
    crimeTypeState.selectedAll = true;
    crimeTypeState.selectedValues = new Set();
  } else {
    crimeTypeState.selectedAll = false;
    crimeTypeState.selectedValues = new Set(Array.from(selectedSet).filter((item) => entries.has(item)));
  }

  syncCrimeTypeHiddenSelect();
  renderCrimeTypeMenu();
  updateCrimeTypeTriggerText();
}

function toggleCrimeTypeSelection(value) {
  if (value === '__ALL__') {
    if (crimeTypeState.selectedAll) {
      crimeTypeState.selectedAll = false;
      crimeTypeState.selectedValues = new Set();
    } else {
      crimeTypeState.selectedAll = true;
      crimeTypeState.selectedValues = new Set();
    }
  } else if (value) {
    if (crimeTypeState.selectedAll) {
      crimeTypeState.selectedAll = false;
      crimeTypeState.selectedValues = new Set([value]);
    } else if (crimeTypeState.selectedValues.has(value)) {
      crimeTypeState.selectedValues.delete(value);
    } else {
      crimeTypeState.selectedValues.add(value);
    }
  }

  syncCrimeTypeHiddenSelect();
  renderCrimeTypeMenu();
  updateCrimeTypeTriggerText();
}

function openCrimeTypeMenu() {
  if (!els.crimeTypeMenu || !els.crimeTypeTrigger) {
    return;
  }
  els.crimeTypeMenu.hidden = false;
  els.crimeTypeTrigger.setAttribute('aria-expanded', 'true');
}

function closeCrimeTypeMenu() {
  if (!els.crimeTypeMenu || !els.crimeTypeTrigger) {
    return;
  }
  els.crimeTypeMenu.hidden = true;
  els.crimeTypeTrigger.setAttribute('aria-expanded', 'false');
}

function toggleCrimeTypeMenu() {
  if (els.crimeTypeMenu.hidden) {
    openCrimeTypeMenu();
  } else {
    closeCrimeTypeMenu();
  }
}

function getFilters() {
  let startYear = toInt(els.startYear.value);
  let endYear = toInt(els.endYear.value);

  if (startYear !== null && endYear !== null && startYear > endYear) {
    [startYear, endYear] = [endYear, startYear];
  }

  return {
    apiBase: API_BASE,
    startYear,
    endYear,
    crimeTypeAllSelected: crimeTypeState.selectedAll,
    crimeTypes: getCrimeTypeSelection(),
    topN: Math.max(3, Math.min(30, toInt(els.topN.value, 10))),
  };
}

function applyDefaults() {
  els.startYear.value = defaults.startYear;
  els.endYear.value = defaults.endYear;
  crimeTypeState.selectedAll = true;
  crimeTypeState.selectedValues = new Set();
  syncCrimeTypeHiddenSelect();
  renderCrimeTypeMenu();
  updateCrimeTypeTriggerText();
  closeCrimeTypeMenu();
  els.topN.value = defaults.topN;
}

function buildUrl(baseUrl, path, query = {}) {
  const url = new URL(path, baseUrl);
  Object.entries(query).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item !== null && item !== undefined && item !== '') {
          url.searchParams.append(key, String(item));
        }
      });
      return;
    }
    if (value !== null && value !== undefined && value !== '') {
      url.searchParams.set(key, String(value));
    }
  });
  return url.toString();
}

async function fetchJson(baseUrl, path, query = {}) {
  const url = buildUrl(baseUrl, path, query);
  const response = await fetch(url, { method: 'GET' });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`请求失败 ${response.status}: ${path} ${text || ''}`.trim());
  }
  return response.json();
}

function shouldUseStaticSnapshot(filters) {
  return (
    filters.startYear === null
    && filters.endYear === null
    && filters.crimeTypeAllSelected === true
    && (!Array.isArray(filters.crimeTypes) || filters.crimeTypes.length === 0)
    && Number(filters.topN) === defaults.topN
  );
}

async function fetchStaticDashboardSnapshot(baseUrl) {
  const url = buildUrl(baseUrl, STATIC_DASHBOARD_SNAPSHOT_PATH);
  const response = await fetch(url, { method: 'GET', cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`静态快照不可用（${response.status}）`);
  }
  return response.json();
}

async function loadDynamicDashboardData(filters) {
  const bundleQuery = {
    start_year: filters.startYear,
    end_year: filters.endYear,
    crime_types: filters.crimeTypes,
    top_n: filters.topN,
  };

  const [health, bundle] = await Promise.all([
    fetchJson(filters.apiBase, '/api/v1/system/health'),
    fetchJson(filters.apiBase, '/api/v1/analysis/dashboard-bundle', bundleQuery),
  ]);

  return {
    source: 'dynamic',
    health,
    ...bundle,
  };
}

async function loadDashboardData(filters) {
  if (shouldUseStaticSnapshot(filters)) {
    try {
      const [health, snapshot] = await Promise.all([
        fetchJson(filters.apiBase, '/api/v1/system/health'),
        fetchStaticDashboardSnapshot(filters.apiBase),
      ]);

      return {
        ...snapshot,
        health,
        source: 'static',
      };
    } catch (error) {
      console.warn('[dashboard] Static snapshot load failed, fallback to dynamic queries.', error);
    }
  }

  return loadDynamicDashboardData(filters);
}

function parseYearFromDateString(text) {
  if (!text) {
    return null;
  }
  const match = String(text).match(/(\d{4})/);
  return match ? Number(match[1]) : null;
}

function buildYearOptions(payload) {
  const years = new Set();

  (payload.annual.data || []).forEach((row) => {
    const year = Number(row.year_num);
    if (Number.isFinite(year)) {
      years.add(year);
    }
  });

  if (years.size === 0) {
    const minYear = parseYearFromDateString(payload.overview.min_occurrence_time);
    const maxYear = parseYearFromDateString(payload.overview.max_occurrence_time);
    if (Number.isFinite(minYear) && Number.isFinite(maxYear) && minYear <= maxYear) {
      for (let year = minYear; year <= maxYear; year += 1) {
        years.add(year);
      }
    }
  }

  if (years.size === 0) {
    const currentYear = new Date().getFullYear();
    for (let year = 2001; year <= currentYear; year += 1) {
      years.add(year);
    }
  }

  return Array.from(years).sort((a, b) => a - b);
}

function updateFilterOptions(payload, filters) {
  const years = buildYearOptions(payload);
  const yearOptions = years.map((year) => ({ value: year, label: `${year}` }));

  setSelectOptions(els.startYear, yearOptions, '全部年份', filters.startYear);
  setSelectOptions(els.endYear, yearOptions, '全部年份', filters.endYear);

  const crimeTypeSet = new Set();

  (payload.typeOptions.data || []).forEach((row) => {
    if (row.primary_type) {
      crimeTypeSet.add(String(row.primary_type));
    }
  });

  (payload.yoy.data || []).forEach((row) => {
    if (row.primary_type) {
      crimeTypeSet.add(String(row.primary_type));
    }
  });

  (Array.isArray(filters.crimeTypes) ? filters.crimeTypes : []).forEach((item) => {
    if (item) {
      crimeTypeSet.add(item);
    }
  });

  const crimeOptions = Array.from(crimeTypeSet)
    .sort((a, b) => translateCrimeType(a).localeCompare(translateCrimeType(b), 'zh-CN'))
    .map((item) => ({ value: item, label: translateCrimeType(item) }));

  const crimeOptionsForSelect = disambiguateDuplicateCrimeLabels(crimeOptions);
  setCrimeTypeOptions(crimeOptionsForSelect, filters.crimeTypes || []);
}

function formatCrimeTypeFilterLabel(crimeTypes, allSelected = true) {
  if (allSelected) {
    return '全部类型';
  }
  if (!Array.isArray(crimeTypes) || crimeTypes.length === 0) {
    return '未勾选类型';
  }
  const translated = crimeTypes.map((item) => translateCrimeType(item));
  if (translated.length <= 3) {
    return translated.join('、');
  }
  return `${translated.slice(0, 3).join('、')} 等${translated.length}类`;
}

function showTooltip(event, html) {
  tooltip.style('opacity', 1).style('left', `${event.clientX}px`).style('top', `${event.clientY - 12}px`).html(html);
}

function hideTooltip() {
  tooltip.style('opacity', 0);
}

function createChartSvg(selector, chartHeight = 310) {
  const container = d3.select(selector);
  container.selectAll('*').remove();

  const width = Math.max(container.node().clientWidth || 420, 280);
  const svg = container.append('svg').attr('viewBox', `0 0 ${width} ${chartHeight}`).attr('preserveAspectRatio', 'xMidYMid meet');

  return { svg, width, height: chartHeight };
}

function drawNoData(selector, message = '暂无可展示数据') {
  const { svg, width, height } = createChartSvg(selector, 220);
  svg.append('text').attr('x', width / 2).attr('y', height / 2).attr('text-anchor', 'middle').attr('fill', '#4d626e').attr('font-size', 14).text(message);
}

function renderLineChart({ selector, data, xKey, yKey, xLabel, yLabel, lineColor }) {
  if (!Array.isArray(data) || data.length === 0) {
    drawNoData(selector);
    return;
  }

  const normalized = data
    .map((d) => ({
      x: Number(d[xKey]),
      y: Number(d[yKey]),
    }))
    .filter((d) => Number.isFinite(d.x) && Number.isFinite(d.y))
    .sort((a, b) => a.x - b.x);

  if (normalized.length === 0) {
    drawNoData(selector);
    return;
  }

  const maxY = d3.max(normalized, (d) => d.y) || 0;
  const yTickSample = formatNumber(maxY);
  const dynamicLeft = Math.max(74, Math.min(108, 20 + yTickSample.length * 7));

  const { svg, width, height } = createChartSvg(selector);
  const margin = { top: 18, right: 16, bottom: 44, left: dynamicLeft };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const x = d3.scaleLinear().domain(d3.extent(normalized, (d) => d.x)).range([0, innerW]);
  const y = d3
    .scaleLinear()
    .domain([0, maxY * 1.08])
    .nice()
    .range([innerH, 0]);

  g.append('g').attr('class', 'grid').call(d3.axisLeft(y).ticks(5).tickSize(-innerW).tickFormat(''));
  g.append('g').attr('class', 'axis').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x).ticks(6).tickFormat(d3.format('d')));
  g.append('g').attr('class', 'axis').call(d3.axisLeft(y).ticks(5));

  g.append('text').attr('x', innerW / 2).attr('y', innerH + 36).attr('fill', '#395767').attr('text-anchor', 'middle').attr('font-size', 12).text(xLabel);
  g.append('text').attr('transform', 'rotate(-90)').attr('x', -innerH / 2).attr('y', -(margin.left - 14)).attr('fill', '#395767').attr('text-anchor', 'middle').attr('font-size', 12).text(yLabel);

  const line = d3
    .line()
    .x((d) => x(d.x))
    .y((d) => y(d.y));

  const path = g.append('path').datum(normalized).attr('fill', 'none').attr('stroke', lineColor).attr('stroke-width', 2.5).attr('d', line);

  const totalLength = path.node().getTotalLength();
  path
    .attr('stroke-dasharray', `${totalLength} ${totalLength}`)
    .attr('stroke-dashoffset', totalLength)
    .transition()
    .duration(900)
    .ease(d3.easeCubicOut)
    .attr('stroke-dashoffset', 0);

  g.selectAll('.point')
    .data(normalized)
    .join('circle')
    .attr('class', 'point')
    .attr('cx', (d) => x(d.x))
    .attr('cy', (d) => y(d.y))
    .attr('r', 0)
    .attr('fill', '#fff')
    .attr('stroke', lineColor)
    .attr('stroke-width', 2)
    .on('mousemove', (event, d) => showTooltip(event, `年份：${d.x}<br/>案件数：${formatNumber(d.y)}`))
    .on('mouseleave', hideTooltip)
    .transition()
    .delay((_, i) => i * 25)
    .duration(260)
    .attr('r', 4);
}

function renderBarChart({ selector, data, xKey, yKey, xLabel, yLabel, color, xFormatter, chartHeight = 310, xTickStep = 1 }) {
  if (!Array.isArray(data) || data.length === 0) {
    drawNoData(selector);
    return;
  }

  const normalized = data
    .map((d) => ({
      x: xFormatter ? xFormatter(d[xKey]) : String(d[xKey]),
      y: Number(d[yKey]),
    }))
    .filter((d) => Number.isFinite(d.y));

  if (normalized.length === 0) {
    drawNoData(selector);
    return;
  }

  const maxY = d3.max(normalized, (d) => d.y) || 0;
  const yTickSample = formatNumber(maxY);
  const dynamicLeft = Math.max(74, Math.min(108, 20 + yTickSample.length * 7));

  const { svg, width, height } = createChartSvg(selector, chartHeight);
  const margin = { top: 18, right: 16, bottom: 56, left: dynamicLeft };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const x = d3.scaleBand().domain(normalized.map((d) => d.x)).range([0, innerW]).padding(0.18);
  const y = d3
    .scaleLinear()
    .domain([0, maxY * 1.08])
    .nice()
    .range([innerH, 0]);

  g.append('g').attr('class', 'grid').call(d3.axisLeft(y).ticks(5).tickSize(-innerW).tickFormat(''));

  const xDomain = normalized.map((d) => d.x);
  const tickValues = xTickStep > 1 ? xDomain.filter((_, i) => i % xTickStep === 0) : xDomain;
  const xAxis = d3.axisBottom(x).tickValues(tickValues);

  const xAxisG = g.append('g').attr('class', 'axis').attr('transform', `translate(0,${innerH})`).call(xAxis);

  if (tickValues.length > 8) {
    xAxisG.selectAll('text').attr('transform', 'translate(-6,6) rotate(-18)').style('text-anchor', 'end');
  }

  g.append('g').attr('class', 'axis').call(d3.axisLeft(y).ticks(5));

  g.append('text').attr('x', innerW / 2).attr('y', innerH + 44).attr('fill', '#395767').attr('text-anchor', 'middle').attr('font-size', 12).text(xLabel);
  g.append('text').attr('transform', 'rotate(-90)').attr('x', -innerH / 2).attr('y', -(margin.left - 14)).attr('fill', '#395767').attr('text-anchor', 'middle').attr('font-size', 12).text(yLabel);

  g.selectAll('.bar')
    .data(normalized)
    .join('rect')
    .attr('class', 'bar')
    .attr('x', (d) => x(d.x))
    .attr('width', x.bandwidth())
    .attr('y', innerH)
    .attr('height', 0)
    .attr('rx', 4)
    .attr('fill', color)
    .on('mousemove', (event, d) => showTooltip(event, `${d.x}<br/>案件数：${formatNumber(d.y)}`))
    .on('mouseleave', hideTooltip)
    .transition()
    .delay((_, i) => i * 20)
    .duration(420)
    .attr('y', (d) => y(d.y))
    .attr('height', (d) => innerH - y(d.y));
}

function renderHorizontalBarChart({ selector, data, labelKey, valueKey, color }) {
  if (!Array.isArray(data) || data.length === 0) {
    drawNoData(selector);
    return;
  }

  const normalized = data
    .map((d) => ({
      label: `警区 ${d[labelKey]}`,
      value: Number(d[valueKey]),
    }))
    .filter((d) => Number.isFinite(d.value));

  if (normalized.length === 0) {
    drawNoData(selector);
    return;
  }

  const sorted = normalized.sort((a, b) => b.value - a.value);
  const { svg, width, height } = createChartSvg(selector, Math.max(300, sorted.length * 30 + 80));
  const margin = { top: 16, right: 20, bottom: 34, left: 84 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const x = d3
    .scaleLinear()
    .domain([0, d3.max(sorted, (d) => d.value) * 1.05])
    .nice()
    .range([0, innerW]);

  const y = d3.scaleBand().domain(sorted.map((d) => d.label)).range([0, innerH]).padding(0.2);

  g.append('g').attr('class', 'grid').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x).ticks(6).tickSize(-innerH).tickFormat(''));
  g.append('g').attr('class', 'axis').call(d3.axisLeft(y));
  g.append('g').attr('class', 'axis').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x).ticks(6));

  g.selectAll('.bar-h')
    .data(sorted)
    .join('rect')
    .attr('class', 'bar-h')
    .attr('x', 0)
    .attr('y', (d) => y(d.label))
    .attr('height', y.bandwidth())
    .attr('width', 0)
    .attr('rx', 4)
    .attr('fill', color)
    .on('mousemove', (event, d) => showTooltip(event, `${d.label}<br/>案件数：${formatNumber(d.value)}`))
    .on('mouseleave', hideTooltip)
    .transition()
    .duration(520)
    .delay((_, i) => i * 40)
    .attr('width', (d) => x(d.value));
}

function renderHeatmapChart({ selector, data }) {
  if (!Array.isArray(data) || data.length === 0) {
    drawNoData(selector);
    return;
  }

  const normalized = data
    .map((d) => ({
      weekday: Number(d.weekday_num),
      hour: Number(d.hour_num),
      value: Number(d.crime_count),
    }))
    .filter((d) => Number.isFinite(d.weekday) && Number.isFinite(d.hour) && Number.isFinite(d.value) && d.weekday >= 1 && d.weekday <= 7 && d.hour >= 0 && d.hour <= 23);

  if (normalized.length === 0) {
    drawNoData(selector);
    return;
  }

  const hours = d3.range(0, 24);
  const days = d3.range(1, 8);
  const valueByCell = new Map(normalized.map((d) => [`${d.weekday}-${d.hour}`, d.value]));
  const cells = [];
  days.forEach((day) => {
    hours.forEach((hour) => {
      cells.push({ day, hour, value: valueByCell.get(`${day}-${hour}`) || 0 });
    });
  });

  const { svg, width, height } = createChartSvg(selector, 390);
  const margin = { top: 20, right: 24, bottom: 66, left: 68 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const x = d3.scaleBand().domain(hours).range([0, innerW]).padding(0.06);
  const y = d3.scaleBand().domain(days).range([0, innerH]).padding(0.06);
  const maxValue = d3.max(cells, (d) => d.value) || 1;
  const color = d3.scaleSequential().domain([0, maxValue]).interpolator(d3.interpolateYlOrRd);

  g.selectAll('.heat-cell')
    .data(cells)
    .join('rect')
    .attr('class', 'heat-cell')
    .attr('x', (d) => x(d.hour))
    .attr('y', (d) => y(d.day))
    .attr('width', x.bandwidth())
    .attr('height', y.bandwidth())
    .attr('rx', 3)
    .attr('fill', '#f6efe0')
    .on('mousemove', (event, d) => {
      showTooltip(event, `${translateWeekday(d.day)} ${d.hour}时<br/>案件数：${formatNumber(d.value)}`);
    })
    .on('mouseleave', hideTooltip)
    .transition()
    .duration(420)
    .delay((_, i) => i * 3)
    .attr('fill', (d) => color(d.value));

  const tickHours = hours.filter((h) => h % 2 === 0);
  g.append('g').attr('class', 'axis').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x).tickValues(tickHours).tickFormat((d) => `${d}`));
  g.append('g').attr('class', 'axis').call(d3.axisLeft(y).tickFormat((d) => translateWeekday(d)));

  g.append('text').attr('x', innerW / 2).attr('y', innerH + 46).attr('fill', '#395767').attr('text-anchor', 'middle').attr('font-size', 12).text('小时');
  g.append('text').attr('transform', 'rotate(-90)').attr('x', -innerH / 2).attr('y', -46).attr('fill', '#395767').attr('text-anchor', 'middle').attr('font-size', 12).text('星期');

  const gradientId = `legend-gradient-${selector.replace(/[^a-zA-Z0-9]/g, '')}`;
  const defs = svg.append('defs');
  const gradient = defs.append('linearGradient').attr('id', gradientId).attr('x1', '0%').attr('x2', '100%').attr('y1', '0%').attr('y2', '0%');

  [0, 0.25, 0.5, 0.75, 1].forEach((offset) => {
    gradient.append('stop').attr('offset', `${offset * 100}%`).attr('stop-color', color(maxValue * offset));
  });

  const legendW = 180;
  const legendH = 10;
  const legendX = width - legendW - 24;
  const legendY = height - 28;

  svg.append('rect').attr('x', legendX).attr('y', legendY).attr('width', legendW).attr('height', legendH).attr('rx', 4).attr('fill', `url(#${gradientId})`);
  const legendScale = d3.scaleLinear().domain([0, maxValue]).range([0, legendW]);
  const legendAxis = d3.axisBottom(legendScale).ticks(4).tickFormat((d) => formatNumber(d));
  svg.append('g').attr('class', 'axis').attr('transform', `translate(${legendX},${legendY + legendH})`).call(legendAxis);
  svg.append('text').attr('x', legendX).attr('y', legendY - 6).attr('fill', '#395767').attr('font-size', 11).text('案件数密度');
}

function renderMultiLineChart({ selector, data }) {
  if (!Array.isArray(data) || data.length === 0) {
    drawNoData(selector);
    return;
  }

  const normalized = data
    .map((d) => ({
      year: Number(d.year_num),
      typeRaw: String(d.primary_type || ''),
      count: Number(d.crime_count),
    }))
    .filter((d) => Number.isFinite(d.year) && d.typeRaw && Number.isFinite(d.count));

  if (normalized.length === 0) {
    drawNoData(selector);
    return;
  }

  const grouped = d3.group(normalized, (d) => d.typeRaw);
  const series = Array.from(grouped, ([typeRaw, values]) => ({
    typeRaw,
    typeZh: translateCrimeType(typeRaw),
    values: values.slice().sort((a, b) => a.year - b.year),
    total: d3.sum(values, (v) => v.count),
  })).sort((a, b) => b.total - a.total);

  const baseWidth = Math.max(d3.select(selector).node().clientWidth || 420, 280);
  const legendColumns = Math.max(1, Math.min(3, Math.floor((baseWidth - 90) / 230)));
  const legendRows = Math.ceil(series.length / legendColumns);
  const chartHeight = Math.max(390, 290 + legendRows * 24 + 96);

  const { svg, width, height } = createChartSvg(selector, chartHeight);
  const margin = { top: 20, right: 18, bottom: 56 + legendRows * 24, left: 80 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const yearExtent = d3.extent(normalized, (d) => d.year);
  const maxCount = d3.max(normalized, (d) => d.count) || 1;

  const x = d3.scaleLinear().domain(yearExtent).nice().range([0, innerW]);
  const y = d3.scaleLinear().domain([0, maxCount * 1.08]).nice().range([innerH, 0]);

  g.append('g').attr('class', 'grid').call(d3.axisLeft(y).ticks(5).tickSize(-innerW).tickFormat(''));
  g.append('g').attr('class', 'axis').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(x).ticks(6).tickFormat(d3.format('d')));
  g.append('g').attr('class', 'axis').call(d3.axisLeft(y).ticks(5).tickFormat((d) => formatCompactCount(d)));

  g.append('text').attr('x', innerW / 2).attr('y', innerH + 36).attr('fill', '#395767').attr('text-anchor', 'middle').attr('font-size', 12).text('年份');
  g.append('text').attr('transform', 'rotate(-90)').attr('x', -innerH / 2).attr('y', -62).attr('fill', '#395767').attr('text-anchor', 'middle').attr('font-size', 12).text('案件数');

  const palette = [...d3.schemeTableau10, ...d3.schemeSet3];
  const color = d3.scaleOrdinal().domain(series.map((s) => s.typeRaw)).range(palette);

  const line = d3
    .line()
    .x((d) => x(d.year))
    .y((d) => y(d.count));

  const lineGroup = g
    .selectAll('.series-line')
    .data(series)
    .join('path')
    .attr('class', 'series-line')
    .attr('fill', 'none')
    .attr('stroke', (d) => color(d.typeRaw))
    .attr('stroke-width', 2.4)
    .attr('d', (d) => line(d.values));

  lineGroup.each(function () {
    const length = this.getTotalLength();
    d3.select(this)
      .attr('stroke-dasharray', `${length} ${length}`)
      .attr('stroke-dashoffset', length)
      .transition()
      .duration(760)
      .ease(d3.easeCubicOut)
      .attr('stroke-dashoffset', 0);
  });

  const pointGroup = g.selectAll('.series-points').data(series).join('g').attr('class', 'series-points').attr('data-type', (d) => d.typeRaw);

  pointGroup
    .selectAll('circle')
    .data((d) => d.values.map((v) => ({ ...v, typeRaw: d.typeRaw, typeZh: d.typeZh })))
    .join('circle')
    .attr('cx', (d) => x(d.year))
    .attr('cy', (d) => y(d.count))
    .attr('r', 3.2)
    .attr('fill', (d) => color(d.typeRaw))
    .on('mousemove', (event, d) => {
      showTooltip(event, `${d.typeZh}<br/>年份：${d.year}<br/>案件数：${formatNumber(d.count)}`);
    })
    .on('mouseleave', hideTooltip);

  const legend = svg.append('g').attr('transform', `translate(${margin.left},${margin.top + innerH + 44})`);
  const legendCellW = innerW / legendColumns;

  const legendItems = legend
    .selectAll('.legend-item')
    .data(series)
    .join('g')
    .attr('class', 'legend-item')
    .attr('transform', (_, i) => {
      const row = Math.floor(i / legendColumns);
      const col = i % legendColumns;
      return `translate(${col * legendCellW},${row * 22})`;
    })
    .style('cursor', 'pointer')
    .on('mouseover', (_, selected) => {
      lineGroup.attr('opacity', (d) => (d.typeRaw === selected.typeRaw ? 1 : 0.14)).attr('stroke-width', (d) => (d.typeRaw === selected.typeRaw ? 3.2 : 2.2));
      pointGroup.attr('opacity', (d) => (d.typeRaw === selected.typeRaw ? 1 : 0.14));
    })
    .on('mouseleave', () => {
      lineGroup.attr('opacity', 1).attr('stroke-width', 2.4);
      pointGroup.attr('opacity', 1);
    });

  legendItems.append('line').attr('x1', 0).attr('x2', 14).attr('y1', -4).attr('y2', -4).attr('stroke-width', 3).attr('stroke', (d) => color(d.typeRaw));
  legendItems
    .append('text')
    .attr('x', 20)
    .attr('y', 0)
    .text((d) => (d.typeZh.length > 14 ? `${d.typeZh.slice(0, 14)}...` : d.typeZh));
}

function renderDonutChart({ selector, data, labelKey, valueKey }) {
  if (!Array.isArray(data) || data.length === 0) {
    drawNoData(selector);
    return;
  }

  const normalized = data
    .map((d) => {
      const rawLabel = String(d[labelKey] || '');
      return {
        rawLabel,
        labelZh: translateCrimeType(rawLabel),
        value: Number(d[valueKey]),
      };
    })
    .filter((d) => d.rawLabel && Number.isFinite(d.value) && d.value > 0);

  if (normalized.length === 0) {
    drawNoData(selector);
    return;
  }

  const legendColumns = window.innerWidth < 900 ? 1 : 2;
  const legendRows = Math.ceil(normalized.length / legendColumns);
  const chartHeight = Math.max(360, 230 + legendRows * 24 + 42);

  const { svg, width, height } = createChartSvg(selector, chartHeight);
  const radius = Math.min(width * 0.2, 94);
  const centerX = width / 2;
  const centerY = 120;

  const color = d3.scaleOrdinal().domain(normalized.map((d) => d.rawLabel)).range([...d3.schemeTableau10, ...d3.schemeSet3]);
  const pie = d3.pie().sort(null).value((d) => d.value);
  const arc = d3.arc().innerRadius(radius * 0.56).outerRadius(radius);
  const arcHover = d3.arc().innerRadius(radius * 0.56).outerRadius(radius + 8);

  const g = svg.append('g').attr('transform', `translate(${centerX},${centerY})`);

  const arcs = g
    .selectAll('path')
    .data(pie(normalized))
    .join('path')
    .attr('fill', (d) => color(d.data.rawLabel))
    .attr('stroke', '#ffffff')
    .attr('stroke-width', 1.5)
    .each(function (d) {
      this._current = d;
    })
    .on('mousemove', function (event, d) {
      d3.select(this).attr('d', arcHover);
      const total = d3.sum(normalized, (v) => v.value);
      const pct = ((d.data.value / total) * 100).toFixed(2);
      showTooltip(event, `${d.data.labelZh}<br/>案件数：${formatNumber(d.data.value)}<br/>占比：${pct}%`);
    })
    .on('mouseleave', function () {
      d3.select(this).attr('d', arc);
      hideTooltip();
    });

  arcs
    .transition()
    .duration(700)
    .attrTween('d', function (d) {
      const interpolate = d3.interpolate({ startAngle: d.startAngle, endAngle: d.startAngle }, d);
      return (t) => arc(interpolate(t));
    });

  const totalText = formatNumber(d3.sum(normalized, (d) => d.value));
  g.append('text').attr('text-anchor', 'middle').attr('dy', -2).attr('fill', '#214858').attr('font-size', 15).attr('font-weight', 700).text('总案件');
  g.append('text').attr('text-anchor', 'middle').attr('dy', 20).attr('fill', '#214858').attr('font-size', 18).attr('font-weight', 700).text(totalText);

  const legendStartY = centerY + radius + 24;
  const legend = svg.append('g').attr('transform', `translate(16,${legendStartY})`);
  const legendCellW = (width - 32) / legendColumns;

  const legendItems = legend
    .selectAll('.legend-item')
    .data(normalized)
    .join('g')
    .attr('class', 'legend-item')
    .attr('transform', (_, i) => {
      const row = Math.floor(i / legendColumns);
      const col = i % legendColumns;
      return `translate(${col * legendCellW},${row * 24})`;
    })
    .style('cursor', 'pointer')
    .on('mouseover', (_, item) => {
      arcs.attr('opacity', (arcData) => (arcData.data.rawLabel === item.rawLabel ? 1 : 0.25));
    })
    .on('mouseleave', () => {
      arcs.attr('opacity', 1);
    });

  legendItems.append('rect').attr('width', 11).attr('height', 11).attr('y', -9).attr('rx', 2).attr('fill', (d) => color(d.rawLabel));
  legendItems
    .append('text')
    .attr('x', 16)
    .attr('y', 0)
    .attr('fill', '#2e4f5c')
    .attr('font-size', 12)
    .text((d) => (d.labelZh.length > 16 ? `${d.labelZh.slice(0, 16)}...` : d.labelZh));
}

function renderOverview(overview, quality) {
  els.kpiTotal.textContent = formatNumber(overview.total_rows);
  const minText = overview.min_occurrence_time || '--';
  const maxText = overview.max_occurrence_time || '--';
  els.kpiRange.textContent = `${minText} 至 ${maxText}`;
  els.kpiTypes.textContent = formatNumber(overview.distinct_crime_types);

  const missingCounts = quality.missing_counts || {};
  const missingTotal = Object.values(missingCounts).reduce((sum, v) => sum + Number(v || 0), 0);
  els.kpiMissing.textContent = formatNumber(missingTotal);
}

function renderConclusions(conclusions) {
  els.conclusionList.innerHTML = '';
  const list = Array.isArray(conclusions.conclusions) ? conclusions.conclusions : [];

  if (list.length === 0) {
    const li = document.createElement('li');
    li.textContent = '暂无结论数据。';
    els.conclusionList.appendChild(li);
    return;
  }

  list.forEach((item) => {
    const li = document.createElement('li');

    const title = document.createElement('div');
    title.className = 'conclusion-title';
    title.textContent = translateConclusionTitle(item.title);

    const body = document.createElement('div');
    body.textContent = translateConclusionText(item.conclusion);

    li.appendChild(title);
    li.appendChild(body);
    els.conclusionList.appendChild(li);
  });
}

function renderInsights(payload) {
  els.insightAnnual.textContent = payload.annual.insight || '';
  els.insightWeekly.textContent = payload.weekly.insight || '';
  els.insightHourly.textContent = payload.hourly.insight || '';
  els.insightType.textContent = payload.typeShare.insight || '';
  els.insightDistrict.textContent = payload.district.insight || '';
  els.insightHeatmap.textContent = payload.heatmap.insight || '';
  els.insightYoy.textContent = payload.yoy.insight || '';
}

function renderCharts(payload) {
  renderLineChart({
    selector: '#chart-annual',
    data: payload.annual.data,
    xKey: 'year_num',
    yKey: 'crime_count',
    xLabel: '年份',
    yLabel: '案件数',
    lineColor: '#0f7b6c',
  });

  const weeklyData = (payload.weekly.data || []).map((row) => ({
    ...row,
    weekday_name_zh: translateWeekday(row.weekday_name || row.weekday_num),
  }));

  renderBarChart({
    selector: '#chart-weekly',
    data: weeklyData,
    xKey: 'weekday_name_zh',
    yKey: 'crime_count',
    xLabel: '星期',
    yLabel: '案件数',
    color: '#145d89',
  });

  renderBarChart({
    selector: '#chart-hourly',
    data: payload.hourly.data,
    xKey: 'hour_num',
    yKey: 'crime_count',
    xLabel: '小时',
    yLabel: '案件数',
    color: '#cf6a32',
    xFormatter: (v) => `${v}时`,
    chartHeight: 370,
    xTickStep: 2,
  });

  renderDonutChart({
    selector: '#chart-type',
    data: payload.typeShare.data,
    labelKey: 'primary_type',
    valueKey: 'crime_count',
  });

  renderHorizontalBarChart({
    selector: '#chart-district',
    data: payload.district.data,
    labelKey: 'district',
    valueKey: 'crime_count',
    color: '#2f7f73',
  });

  renderHeatmapChart({
    selector: '#chart-heatmap',
    data: payload.heatmap.data,
  });

  renderMultiLineChart({
    selector: '#chart-yoy',
    data: payload.yoy.data,
  });
}

function renderAll(payload) {
  currentData = payload;
  updateFilterOptions(payload, currentFilters || getFilters());
  renderOverview(payload.overview, payload.quality);
  renderInsights(payload);
  renderCharts(payload);
  renderConclusions(payload.conclusions);
}

async function refreshDashboard() {
  const filters = getFilters();
  currentFilters = filters;

  setStatus('正在请求后端数据，请稍候...');

  try {
    const payload = await loadDashboardData(filters);
    renderAll(payload);

    const ok = payload.health.status === 'ok' && payload.health.database === 'ok';
    if (ok) {
      setHealth('服务状态：连接正常', 'success');
    } else {
      setHealth('服务状态：服务在线，数据库异常', 'error');
    }

    const rangeText = [filters.startYear || '全部', filters.endYear || '全部'].join(' ~ ');
    const crimeText = formatCrimeTypeFilterLabel(filters.crimeTypes, filters.crimeTypeAllSelected);
    const sourceText = payload.source === 'static' ? '（静态快照）' : '';
    setStatus(`更新完成${sourceText}。筛选范围：${rangeText}；犯罪类型：${crimeText}`);
  } catch (error) {
    console.error(error);
    setHealth('服务状态：请求失败', 'error');
    setStatus(`加载失败：${error.message}`, true);
  }
}

function bindEvents() {
  if (!els.crimeTypeTrigger || !els.crimeTypeMenu || !els.crimeTypeDropdown) {
    return;
  }

  els.crimeTypeTrigger.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    toggleCrimeTypeMenu();
  });

  els.crimeTypeMenu.addEventListener('click', (event) => {
    event.stopPropagation();
    const optionEl = event.target.closest('.multi-select-option');
    if (!optionEl) {
      return;
    }
    toggleCrimeTypeSelection(optionEl.dataset.value || '');
  });

  els.crimeTypeMenu.addEventListener('keydown', (event) => {
    event.stopPropagation();
    if (event.key !== 'Enter' && event.key !== ' ') {
      return;
    }
    const optionEl = event.target.closest('.multi-select-option');
    if (!optionEl) {
      return;
    }
    event.preventDefault();
    toggleCrimeTypeSelection(optionEl.dataset.value || '');
  });

  document.addEventListener('click', (event) => {
    const path = typeof event.composedPath === 'function' ? event.composedPath() : [];
    const clickedInside = path.includes(els.crimeTypeDropdown)
      || (event.target instanceof Node && els.crimeTypeDropdown.contains(event.target));
    if (!clickedInside) {
      closeCrimeTypeMenu();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeCrimeTypeMenu();
    }
  });

  els.form.addEventListener('submit', async (event) => {
    event.preventDefault();
    closeCrimeTypeMenu();
    await refreshDashboard();
  });

  els.resetBtn.addEventListener('click', async () => {
    applyDefaults();
    await refreshDashboard();
  });

  window.addEventListener('resize', () => {
    if (currentData && currentFilters) {
      renderCharts(currentData);
    }
  });
}

async function init() {
  ensureCrimeTypeDropdownElements();
  applyDefaults();
  bindEvents();
  await refreshDashboard();
}

init();
