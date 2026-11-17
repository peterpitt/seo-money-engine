"""給訪客的多語言假日行事曆頁面：區塊切換國家，每個語言一個網址。

設定（site.yaml）：
  calendar_page:
    countries: [us, ae, it, jp]
    languages: [en, zh-TW, ja, it, ar]   # 第一個是預設版本（/calendar/）
    year: 2027

翻譯（data/holidays/i18n.yaml）：
  countries: {jp: {ja: 日本, it: Giappone, ar: اليابان}}
  holidays: {"Showa Day": {it: "Giorno di Shōwa", ar: "يوم شووا"}}
假日名稱的優先順序：繁中用 name_zh → 頁面語言 = 該國語言時用當地名稱 → i18n.yaml → 英文。
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .calendar import Calendar, HolidayEntry, _COUNTRY_COLORS, _FALLBACK_COLORS, long_breaks

TEMPLATES = Path(__file__).parent / "templates"

LANGUAGES: dict[str, dict] = {
    "en": {
        "label": "English", "dir": "ltr",
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "title": "Public Holidays {year}", "subtitle": "Pick a country to see every holiday and long weekend.",
        "description": "Public holidays {year} for {countries}: next holiday countdown, full list and long weekends.",
        "countries": "Countries", "next": "Next holiday", "holidays": "Holidays", "long": "Long weekends",
        "days": "{n} days", "leave": "+{k} leave day", "leave_pl": "+{k} leave days", "expected": "Expected",
        "moved": "Moved", "in": "in {n} days", "in1": "tomorrow", "today": "today", "none": "No more dates yet",
        "guide": "Full guide", "note": "From official government calendars. Expected dates can still change.",
        "nav": "Holiday calendar", "articles": "Guides & articles",
        "me": "Your time", "ahead": "{h} ahead", "behind": "{h} behind", "same": "Same as you", "hours": "{n} h",
        "rail": "Holiday countdown", "upcoming": "Coming up", "resource_note": "Travel resource links coming soon",
    },
    "zh-TW": {
        "label": "繁體中文", "dir": "ltr",
        "weekdays": list("一二三四五六日"), "months": [f"{m}月" for m in range(1, 13)],
        "title": "{year} 國定假日", "subtitle": "選一個國家，所有假日和連假一次看。",
        "description": "{year} 國定假日：{countries}。下一個假日倒數、全年假日表與連假。",
        "countries": "國家", "next": "下一個假日", "holidays": "假日", "long": "連假",
        "days": "{n} 天", "leave": "請 {k} 天假", "leave_pl": "請 {k} 天假", "expected": "預估",
        "moved": "調整", "in": "還有 {n} 天", "in1": "明天", "today": "就是今天", "none": "目前沒有之後的日期",
        "guide": "完整攻略", "note": "依各國政府公告整理，預估日期仍可能變動。",
        "nav": "假日行事曆", "articles": "假日攻略文章",
        "me": "你的時間", "ahead": "快 {h}", "behind": "慢 {h}", "same": "跟你同時間", "hours": "{n} 小時",
        "rail": "節慶倒數", "upcoming": "近期假日", "resource_note": "旅遊資訊連結準備中",
    },
    "ja": {
        "label": "日本語", "dir": "ltr",
        "weekdays": list("月火水木金土日"), "months": [f"{m}月" for m in range(1, 13)],
        "title": "{year}年の祝日", "subtitle": "国を選ぶと、祝日と連休がひと目でわかります。",
        "description": "{year}年の祝日：{countries}。次の祝日までの日数、祝日一覧、連休。",
        "countries": "国", "next": "次の祝日", "holidays": "祝日", "long": "連休",
        "days": "{n}日間", "leave": "休暇{k}日", "leave_pl": "休暇{k}日", "expected": "予定",
        "moved": "振替", "in": "あと{n}日", "in1": "明日", "today": "今日", "none": "以降の日付はまだありません",
        "guide": "詳しいガイド（英語）", "note": "各国政府の公式発表に基づきます。予定日は変わる可能性があります。",
        "nav": "祝日カレンダー", "articles": "ガイド記事",
        "me": "あなたの時刻", "ahead": "{h}進んでいる", "behind": "{h}遅れている", "same": "同じ時刻", "hours": "{n}時間",
        "rail": "祝日カウントダウン", "upcoming": "直近の祝日", "resource_note": "旅行情報のリンクは準備中です",
    },
    "it": {
        "label": "Italiano", "dir": "ltr",
        "weekdays": ["lun", "mar", "mer", "gio", "ven", "sab", "dom"],
        "months": ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"],
        "title": "Festività {year}", "subtitle": "Scegli un paese per vedere festività e ponti.",
        "description": "Festività {year}: {countries}. Conto alla rovescia, elenco completo e ponti.",
        "countries": "Paesi", "next": "Prossima festività", "holidays": "Festività", "long": "Ponti e weekend lunghi",
        "days": "{n} giorni", "leave": "+{k} giorno di ferie", "leave_pl": "+{k} giorni di ferie", "expected": "Prevista",
        "moved": "Spostata", "in": "tra {n} giorni", "in1": "domani", "today": "oggi", "none": "Nessuna data successiva",
        "guide": "Guida completa (in inglese)", "note": "Dai calendari ufficiali dei governi. Le date previste possono cambiare.",
        "nav": "Calendario festività", "articles": "Guide e articoli",
        "me": "La tua ora", "ahead": "+{h} rispetto a te", "behind": "−{h} rispetto a te", "same": "Stessa ora", "hours": "{n} h",
        "rail": "Conto alla rovescia", "upcoming": "Prossime festività", "resource_note": "Link alle risorse di viaggio in arrivo",
    },
    "ar": {
        "label": "العربية", "dir": "rtl",
        "weekdays": ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"],
        "months": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
        "title": "العطلات الرسمية {year}", "subtitle": "اختر دولة لعرض جميع العطلات والإجازات الطويلة.",
        "description": "العطلات الرسمية {year}: {countries}. العد التنازلي والقائمة الكاملة والإجازات الطويلة.",
        "countries": "الدول", "next": "العطلة القادمة", "holidays": "العطلات", "long": "إجازات طويلة",
        "days": "{n} أيام", "leave": "+{k} يوم إجازة", "leave_pl": "+{k} أيام إجازة", "expected": "متوقع",
        "moved": "منقولة", "in": "بعد {n} يوم", "in1": "غدًا", "today": "اليوم", "none": "لا توجد تواريخ لاحقة بعد",
        "guide": "الدليل الكامل (بالإنجليزية)", "note": "من التقويمات الرسمية للحكومات. قد تتغير التواريخ المتوقعة.",
        "nav": "تقويم العطلات", "articles": "الأدلة والمقالات",
        "me": "توقيتك", "ahead": "متقدم {h}", "behind": "متأخر {h}", "same": "نفس توقيتك", "hours": "{n} ساعة",
        "rail": "العد التنازلي للعطلات", "upcoming": "العطلات القادمة", "resource_note": "روابط معلومات السفر قيد الإعداد",
    },
}


@dataclass
class CalendarPageConfig:
    countries: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=lambda: ["en"])
    year: int | str | None = None   # 整數＝固定年份；"auto"＝依今天自動選（10 月起改顯示明年）
    sort: str = "config"          # config＝照 countries 的順序；utc＝依標準時區由西到東

    def __post_init__(self) -> None:
        if self.sort not in ("config", "utc"):
            raise ValueError(f"calendar_page.sort must be 'config' or 'utc', got {self.sort!r}")
        unknown = [lang for lang in self.languages if lang not in LANGUAGES]
        if unknown:
            raise ValueError(f"unsupported calendar language(s): {', '.join(unknown)} (supported: {', '.join(LANGUAGES)})")

    @classmethod
    def from_mapping(cls, data: Mapping | None) -> "CalendarPageConfig | None":
        if not data:
            return None
        return cls(countries=[str(c) for c in data.get("countries") or []],
                   languages=[str(lang) for lang in data.get("languages") or ["en"]],
                   year=_parse_year(data.get("year")),
                   sort=str(data.get("sort") or "config"))

    def default_lang(self, site_default: str = "") -> str:
        """languages 的第一個語言就是 /calendar/ 的預設版本（也是 x-default）。"""
        return self.languages[0]


SWITCH_MONTH = 10   # 10 月起，行事曆預設顯示明年（「明年連假」的搜尋從這時開始變多）


def _parse_year(raw) -> int | str | None:
    if raw in (None, ""):
        return None
    if str(raw).strip().lower() == "auto":
        return "auto"
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"calendar_page.year must be a year like 2027 or 'auto', got {raw!r}") from None


def pick_years(available: list[int], setting, today: dt.date) -> tuple[list[int], int]:
    """回傳（要顯示的年份, 預設年份）。過去的年份不顯示；auto 時 10 月起預設明年。"""
    if not available:
        return [], today.year
    shown = [y for y in available if y >= today.year] or available[-1:]
    if isinstance(setting, int) and setting in available:
        return sorted(set(shown) | {setting}), setting
    if setting == "auto" or setting is None:
        nxt = today.year + 1
        if today.month >= SWITCH_MONTH and nxt in shown:
            return shown, nxt
        if today.year in shown:
            return shown, today.year
    return shown, shown[0] if setting == "auto" or setting is None else shown[-1]


def load_i18n(project_dir: str | Path) -> dict:
    path = Path(project_dir) / "data" / "holidays" / "i18n.yaml"
    if not path.exists():
        return {"countries": {}, "holidays": {}, "cities": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {"countries": data.get("countries") or {}, "holidays": data.get("holidays") or {},
            "cities": data.get("cities") or {}}


def grid_columns(n: int) -> int:
    """國家卡片的欄數：4 或 3 欄中，最後一排空位最少的（9 國 → 3×3）。"""
    options = [c for c in (4, 3, 2) if c <= n] or [1]
    return min(options, key=lambda c: ((-n) % c, -c))


def standard_offset(timezone: str, year: int) -> int:
    """標準時間（非夏令）的 UTC 分鐘數。取一月與七月較小的那個，南北半球都適用。"""
    from zoneinfo import ZoneInfo

    zone = ZoneInfo(timezone)
    return min(int(zone.utcoffset(dt.datetime(year, m, 15, 12)).total_seconds() // 60) for m in (1, 7))


def utc_label(timezone: str, year: int) -> str:
    """「UTC+9」；有夏令時間的地區顯示冬／夏兩個值，例如「UTC−5/−4」。"""
    from zoneinfo import ZoneInfo

    zone = ZoneInfo(timezone)
    offsets = sorted({zone.utcoffset(dt.datetime(year, m, 15, 12)) for m in (1, 7)})

    def fmt(off: dt.timedelta, sign_always: bool = True) -> str:
        minutes = int(off.total_seconds() // 60)
        sign = "+" if minutes >= 0 else "−"
        h, m = divmod(abs(minutes), 60)
        return f"{sign}{h}" + (f":{m:02d}" if m else "")

    return "UTC" + "/".join(fmt(o) for o in offsets)


def localized_city(cal: Calendar, lang: str, i18n: Mapping) -> str:
    if lang == "en" or not cal.city:
        return cal.city
    if _is_zh(lang) and cal.city_zh:
        return cal.city_zh
    return (i18n.get("cities", {}).get(cal.city) or {}).get(lang) or cal.city


def _is_zh(lang: str) -> bool:
    return lang.lower().startswith("zh")


def fmt_day(day: dt.date, lang: str) -> str:
    L = LANGUAGES[lang]
    wd, mon = L["weekdays"][day.weekday()], L["months"][day.month - 1]
    if lang == "en":
        return f"{wd}, {mon} {day.day}"
    if _is_zh(lang):
        return f"{day.month}/{day.day}（{wd}）"
    if lang == "ja":
        return f"{day.month}月{day.day}日（{wd}）"
    return f"{wd} {day.day} {mon}"


def fmt_span(start: dt.date, end: dt.date, lang: str) -> str:
    return fmt_day(start, lang) if start == end else f"{fmt_day(start, lang)} – {fmt_day(end, lang)}"


def localized_country(cal: Calendar, lang: str, i18n: Mapping) -> str:
    if lang == "en":
        return cal.short or cal.country
    if _is_zh(lang):
        return cal.country_zh or cal.country
    return (i18n.get("countries", {}).get(cal.code) or {}).get(lang) or cal.short or cal.country


def localized_holiday(entry: HolidayEntry, cal: Calendar, lang: str, i18n: Mapping) -> str:
    if lang == "en":
        return entry.name
    if _is_zh(lang) and entry.name_zh:
        return entry.name_zh          # 中文頁用常用名（台灣假日的正式名稱會以小字顯示）
    if entry.local and cal.language and lang.split("-")[0] == cal.language.split("-")[0]:
        return entry.local
    return (i18n.get("holidays", {}).get(entry.name) or {}).get(lang) or entry.name


def page_path(lang: str, default_lang: str) -> str:
    # 預設語言的行事曆就是網站首頁（/）；其他語言放 /calendar/<語言>/
    return "/" if lang == default_lang else f"/calendar/{lang.lower()}/"


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.globals["asset_v"] = hashlib.sha1((TEMPLATES / "style.css").read_bytes()).hexdigest()[:8]
    return env


def _next(cal: Calendar, today: dt.date) -> HolidayEntry | None:
    return next((e for e in cal.entries_all if e.end >= today), None)


def _in_days(entry: HolidayEntry | None, today: dt.date, t: Mapping) -> str:
    if not entry:
        return t["none"]
    n = (entry.start - today).days
    return t["today"] if n <= 0 else t["in1"] if n == 1 else t["in"].format(n=n)


def render_calendar_page(site_name: str, base_url: str, calendars: Mapping[str, Calendar], i18n: Mapping,
                         lang: str, page: CalendarPageConfig, today: dt.date | None = None,
                         site=None, nav_to: str | None = None) -> str:
    today = today or dt.date.today()
    t = LANGUAGES[lang]
    site = site or SimpleNamespace(name=site_name, base_url=base_url.rstrip("/"), default_lang="en", description="",
                                   author="", ga4="", adsense=SimpleNamespace(enabled=False, client=""))
    default_lang = page.default_lang(getattr(site, "default_lang", "en"))
    codes = page.countries or list(calendars)
    missing = [c for c in codes if c not in calendars]
    if missing:
        raise ValueError(f"calendar page: unknown countries {', '.join(missing)}")
    years, focus = pick_years(sorted({y for c in codes for y in calendars[c].years()}), page.year, today)
    if page.sort == "utc":
        # 由西到東；同時區照設定順序；沒有時區的放最後
        rank = {c: i for i, c in enumerate(codes)}
        codes = sorted(codes, key=lambda c: (calendars[c].timezone == "",
                                             standard_offset(calendars[c].timezone, focus) if calendars[c].timezone else 0,
                                             rank[c]))

    spare = iter(_FALLBACK_COLORS)
    countries = []
    for code in codes:
        cal = calendars[code]
        nxt = _next(cal, today)
        year_blocks = []
        for y in years:
            entries = cal.entries(y)
            if not entries:
                continue
            total = 366 if dt.date(y, 12, 31).timetuple().tm_yday == 366 else 365
            rows = []
            for i, e in enumerate(entries):
                name = localized_holiday(e, cal, lang, i18n)
                rows.append({
                    "start": e.start.isoformat(), "end": e.end.isoformat(), "i": i,
                    "date": fmt_span(e.start, e.end, lang), "name": name,
                    "local": e.local if e.local and e.local != name else "",
                    "expected": e.status == "estimated",
                    "moved": fmt_day(e.actual, lang) if e.actual and e.actual != e.start else "",
                    "pos": round((e.start.timetuple().tm_yday - 1) / total * 100, 2),
                })
            chips = []
            for b in long_breaks(cal, y):
                if b.start.year != y:
                    continue
                leave = ""
                if b.leave_days:
                    leave = (t["leave"] if b.leave_days == 1 else t["leave_pl"]).format(k=b.leave_days)
                chips.append({"span": fmt_span(b.start, b.end, lang), "days": t["days"].format(n=b.length),
                              "leave": leave, "leave_dates": ", ".join(fmt_day(d, lang) for d in b.leave_dates)})
            year_blocks.append({"year": y, "default": y == focus, "rows": rows, "chips": chips})
        countries.append({
            "code": code, "name": localized_country(cal, lang, i18n),
            "color": _COUNTRY_COLORS.get(code) or next(spare, "#64748b"),
            "next_name": localized_holiday(nxt, cal, lang, i18n) if nxt else t["none"],
            "next_date": fmt_span(nxt.start, nxt.end, lang) if nxt else "",
            "next_in": _in_days(nxt, today, t),
            "upcoming": [
                {"date": fmt_span(e.start, e.end, lang), "name": localized_holiday(e, cal, lang, i18n)}
                for e in cal.entries_all if e.end >= today
            ][:3],
            "years": year_blocks,
            "page": cal.page_for(lang) or cal.page_for("en"),
            "tz": cal.timezone, "city": localized_city(cal, lang, i18n),
            "utc": utc_label(cal.timezone, focus) if cal.timezone else "",
        })

    names = ", ".join(c["name"] for c in countries)
    langs = [{"code": code, "label": LANGUAGES[code]["label"], "href": page_path(code, default_lang),
              "abs": site.base_url + page_path(code, default_lang), "current": code == lang}
             for code in page.languages]
    js_strings = json.dumps({**{k: t[k] for k in ("in", "in1", "today", "none", "ahead", "behind", "same", "hours")},
                             "lang": lang}, ensure_ascii=False)
    return _env().get_template("calendar_page.html").render(
        site=site, page_lang=lang, page_dir=t["dir"], t=t, year=focus, years=[b for b in years],
        title=t["title"].format(year=focus), description=t["description"].format(year=focus, countries=names),
        canonical=site.base_url + page_path(lang, default_lang),
        x_default=site.base_url + page_path(default_lang, default_lang),
        langs=langs, countries=countries, js_strings=js_strings,
        clocks=[c for c in countries if c["tz"]], cols=grid_columns(len(countries)),
        nav_link=(nav_to, t["articles"]) if nav_to else (page_path(lang, default_lang), t["nav"]),
    )
