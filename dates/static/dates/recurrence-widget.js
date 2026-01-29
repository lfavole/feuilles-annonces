const FRENCH = {
    dayNames: ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"],
    monthNames: ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    tokens: {
        SKIP: /^[ \r\n\t]+|^\.$/,
        number: /^[1-9][0-9]*/,
        numberAsText: /^(un|deux|trois)/i,
        every: /^(chaque|tous?t?e?s?\s*le)s?/i,
        "day(s)": /^jours?/i,
        "weekday(s)": /^jours? ouvrables?/i,
        "week(s)": /^semaines?/i,
        "hour(s)": /^heures?/i,
        "minute(s)": /^min(ute)?s?/i,
        "month(s)": /^mois?/i,
        "year(s)": /^ans?|ann[ée]es?/i,
        on: /^(le|en|dans)/i,
        at: /^(à|a)/i,
        the: /^(le|la|les)/i,
        first: /^(premi[eè]re?|1[eè]?re?)/i,
        second: /^(seconde?|deuxième|2e)/i,
        third: /^(troisième|3e)/i,
        nth: /^([1-9][0-9]*)(\.|er|re|e|ème)/i,
        last: /^(dernier|dernière)/i,
        for: /^(pendant|pour)/i,
        "time(s)": /^(x|fois|occurrences?|répétitions?)/i,
        until: /^(jusqu'à|jusqu'au)/i,
        monday: /^lu(n(di)?)?s?\.?/i,
        tuesday: /^ma(r(di)?)?s?\.?/i,
        wednesday: /^me(r(credi)?)?s?\.?/i,
        thursday: /^jeu(di)?s?\.?/i,
        friday: /^ve(n(dredi)?)?s?\.?/i,
        saturday: /^sa(m(edi)?)?s?\.?/i,
        sunday: /^di(m(anche)?)?s?\.?/i,
        january: /^jan(vier)?\.?/i,
        february: /^f[ée]v(rier)?\.?/i,
        march: /^mar(s)?\.?/i,
        april: /^avr(il)?\.?/i,
        may: /^mai\.?/i,
        june: /^juin\.?/i,
        july: /^juil(let)?\.?/i,
        august: /^a?o[ûu]te?\.?/i,
        september: /^sep(t([ea]mbre)?)?\.?/i,
        october: /^oct(obre)?\.?/i,
        november: /^nov([ea]mbre)?\.?/i,
        december: /^d[ée]c([ea]mbre)?\.?/i,
        comma: /^(,\s*|(et|ou)\s*)+/i,
    },
};

function recurrenceWidgetGettext(text) {
    return {
        and: "et",
        "(~ approximate)": "(~ environ)",
        day: "jour",
        days: "jours",
        every: "chaque",
        for: "pour",
        hour: "heure",
        hours: "heures",
        in: "dans",
        last: "dernier",
        minute: "minute",
        minutes: "minutes",
        month: "mois",
        months: "mois",
        nd: "",
        on: "le",
        "on the": "le",
        or: "ou",
        rd: "",
        st: "er",
        th: "",
        the: "",
        time: "fois",
        times: "fois",
        until: "jusqu'à",
        week: "semaine",
        weeks: "semaines",
        weekday: "jour ouvrable",
        weekdays: "jours ouvrables",
        year: "an",
        years: "ans",
    }[text] ?? text;
}

function rruleApp() {
    return {
        rules: [],
        editingId: null,
        showPreview: false,
        daysList: [
            {l: "Lun", v: 0},
            {l: "Mar", v: 1},
            {l: "Mer", v: 2},
            {l: "Jeu", v: 3},
            {l: "Ven", v: 4},
            {l: "Sam", v: 5},
            {l: "Dim", v: 6},
        ],
        posList: [
            {l: "1er", v: 1},
            {l: "2e", v: 2},
            {l: "3e", v: 3},
            {l: "4e", v: 4},
            {l: "5e", v: 5},
            {l: "Der", v: -1},
            {l: "A.Der", v: -2},
            {l: "-3e", v: -3},
            {l: "-4e", v: -4},
            {l: "-5e", v: -5},
        ],

        deserializeRule(data) {
            return new rrule.RRule({
                freq: rrule.RRule[data.freq],
                interval: data.interval,
                byweekday: data.byweekday.length ? data.byweekday : null,
                bymonthday: data.bymonthday.length ? data.bymonthday : null,
                bymonth: data.bymonth.length ? data.bymonth : null,
                bysetpos: data.bysetpos.length ? data.bysetpos : null,
            });
        },

        serializeRule(rule, type) {
            if (type == "ONCE") return rule.dtstart;
            return {
                id: crypto.randomUUID(),
                type: type || "INC",
                freq: rule instanceof Date ? "ONCE" : rrule.Frequency[+rule?.options?.freq] || rule?.options?.freq || "WEEKLY",
                interval: rule?.options?.interval || 1,
                dtstart: ((rule instanceof Date ? rule : rule?.options?.dtstart || new Date()).toISOString?.() || "").split("T")[0],
                byweekday: (rule?.options?.byweekday || []).map(d => isNaN(+d) ? d.weekday : d),
                bymonthday: rule?.options?.bymonthday || [],
                bymonth: rule?.options?.bymonth || [],
                bysetpos: rule?.options?.bysetpos || [],
            };
        },

        getRSet(exclude) {
            const rset = new rrule.RRuleSet();
            for (const data of this.rules) {
                if (exclude?.includes?.(data)) continue;
                const rule = this.deserializeRule(data);
                rset[(data.type == "INC" ? "r" : "ex") + (rule instanceof Date ? "date" : "rule")](rule);
            }
            return rset;
        },

        get rset() {
            return this.getRSet();
        },

        get rfcString() {
            return this.rset.toString();
        },

        set rfcString(value) {
            this.rules = this.parseRFC(value);
        },

        get occurrences() {
            let date = new Date();
            date.setFullYear(date.getFullYear() + 1);
            const max = date.getTime();
            return this.rset.all(d => d.getTime() < max).map(d => d.toLocaleDateString("fr-FR"));
        },

        removeRule(index) {
            this.rules.splice(index, 1);
        },

        toggleValue(list, val) {
            const idx = list.indexOf(val);
            if (idx > -1)
                list.splice(idx, 1);
            else
                list.push(val);
        },

        isAmbiguous(rule) {
            if (rule.freq == "ONCE") return false;

            const r = this.deserializeRule(rule);
            const occ1 = r.all((d, i) => i < 2);
            if (occ1.length < 2) return false;

            const nextDay = new Date(r.options.dtstart);
            nextDay.setDate(nextDay.getDate() + 1);
            const r2 = new rrule.RRule({...r.origOptions, dtstart: nextDay});
            const occ2 = r2.all((d, i) => i < 2);
            const targetTime = occ1[1].getTime();
            return !occ2.some(d => d.getTime() == targetTime);
        },

        isUseful(rule) {
            const ruleIndex = this.rules.indexOf(rule);
            if (this.rules.some((r, i) => {
                if (r.id == rule.id || i <= ruleIndex) return false;
                for (let key of Object.keys(r)) {
                    if (r[key] != rule[key])
                        return false;
                }
                return true;
            }))
                return false;
            let date = new Date();
            date.setFullYear(date.getFullYear() + 1);
            const max = date.getTime();
            const getDates = rset => rset.all(d => d.getTime() < max).map(d => d.getTime());
            const a = getDates(this.rset);
            const b = getDates(this.getRSet([rule]));
            if (a.length != b.length) return true;
            return a.some((v, i) => v != b[i]);
        },

        getRuleLabel(rule) {
            if (rule.freq == "ONCE") return `Le ${new Date(rule.dtstart).toLocaleDateString("fr-FR")}`;
            return this.deserializeRule(rule).toText(recurrenceWidgetGettext, FRENCH);
        },

        parseRFC(val) {
            if (!val) return [];

            const parsed = rrule.rrulestr(val, {forceset: true});

            return [
                ...[...parsed._rdate, ...parsed._rrule].map(r => this.serializeRule(r, "INC")),
                ...[...parsed._exdate, ...parsed._exrule].map(r => this.serializeRule(r, "EXC")),
            ];
        }
    };
}

window.addEventListener("DOMContentLoaded", function() {
    const template = document.getElementById("recurrence-widget-template");
    for (const input of document.querySelectorAll(".recurrence-widget")) {
        input.parentElement.setAttribute("x-data", "rruleApp()");
        input.setAttribute("x-model.fill", "rfcString");
        input.style.display = "none";
        input.after(template.content);
    }
});
