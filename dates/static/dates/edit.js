document.addEventListener("alpine:init", async () => {
    Alpine.data("announcementApp", () => {
        let data = {
            view: "weekly",
            restoreIgnoredEvents: false,
            celebrants: null,
            daysOfWeek: ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"],
            parishes: [
                { name: "Embrunais", locations: ["Embrun", "Châteauroux", "Saint-André", "Saint-Sauveur", "Baratier"] },
                { name: "Lac", locations: ["Savines", "Crots", "Puy-Sanières", "Puy-Saint-Eusèbe"] }
            ],
            currentStartDate: null,
            currentMonthDate: null,
            modifications: {},
            events: null,
            globalNote: "<p>Ajoutez une note générale ou un édito ici...</p>",

            init() {
                const saturday = new Date();
                while(saturday.getDay() != 6) saturday.setDate(saturday.getDate() + 1);
                this.currentStartDate = saturday;
                this.currentMonthDate = new Date();
                this.currentMonthDate.setDate(1);
            },

            changeWeek(days) {
                const d = new Date(this.currentStartDate);
                d.setDate(d.getDate() + days);
                this.currentStartDate = d;
            },

            changeMonth(delta) {
                const d = new Date(this.currentMonthDate);
                d.setMonth(d.getMonth() + delta);
                this.currentMonthDate = d;
            },

            get calendarDays() {
                const list = [];
                if (!this.currentStartDate) return list;
                for (let i = 0; i < 9; i++) {
                    const d = new Date(this.currentStartDate);
                    d.setDate(d.getDate() + i);
                    list.push({
                        name: this.daysOfWeek[d.getDay()],
                        formattedDate: d.toLocaleDateString("fr-FR", { day: "numeric", month: "long" }),
                        dateKey: d.toISOString().split("T")[0],
                    });
                }
                return list;
            },

            get monthWeekends() {
                const month = this.currentMonthDate.getMonth();
                const weekends = [];
                let curr = new Date(this.currentMonthDate);
                curr.setDate(1);
                while(curr.getDay() != 6) curr.setDate(curr.getDate() - 1);

                for (let i = 0; i < 5; i++) {
                    const sat = new Date(curr);
                    const sun = new Date(curr);
                    sun.setDate(sun.getDate() + 1);
                    if (sat.getMonth() == month || sun.getMonth() == month) {
                        weekends.push({
                            date: sat,
                            key: sat.toISOString().split("T")[0],
                            label: sat.getDate() + "/" + (sat.getMonth()+1),
                        });
                        weekends.push({
                            date: sun,
                            key: sun.toISOString().split("T")[0],
                            label: sun.getDate() + "/" + (sun.getMonth()+1),
                        });
                    }
                    curr.setDate(curr.getDate() + 7);
                }
                return weekends;
            },

            formatRange(start) {
                if(!start) return "";
                let d2 = new Date(start); d2.setDate(d2.getDate()+8);
                return "du " + start.toLocaleDateString("fr-FR", {day:"numeric", month:"long"}) + " au " + d2.toLocaleDateString("fr-FR", {day:"numeric", month:"long"});
            },

            getEventsForDay(dayKey, part = "all") {
                const d = new Date(dayKey);
                let dayIndex = d.getDay();

                let events = this.events
                    .filter(e => e.start_date == dayKey && !e.ignored)
                    .filter(e => !e.ignored)
                    .sort((a, b) => a.start_time.localeCompare(b.start_time));

                if (d.getDay() == 6) {
                    let start = events.filter(e => e.start_time < "18:00");
                    let end = events.filter(e => e.start_time >= "18:00");
                    if (this.currentStartDate.toISOString().split("T")[0] == dayKey)
                        start = [];
                    if (!start.length && !end.length)
                        return ["DAY", "ADD", "ORD"];
                    if (start.length && !end.length)
                        return ["DAY", ...start, "ADD", "ORD"];
                    if (!start.length && end.length)
                        return ["ORD", "DAY", ...end, "ADD"];
                    return [
                        "DAY",
                        ...start,
                        "ADD",
                        "ORD",
                        "DAY'",
                        ...end,
                    ];
                }

                return ["DAY", ...events, "ADD"];
            },

            parseTitle(title) {
                if (!title) return "";
                const match = (
                    title
                    .replace(/\bau(?=\W+[A-Z])/g, "à Le")
                    .replace(/\baux(?=\W+[A-Z])/g, "à Les")
                    .replace(/\bau\b/g, "à le")
                    .replace(/\baux\b/g, "à les")
                    .match(/ à (?:((?:l'|le|la|les)?\s*.*?)\s*(?:de\s|d'))?\s*(.*?)(?:\s*\((.*?)\))?$/i)
                );
                return match ? {
                    location: match[2],
                    extra: match[1] || match[3],
                } : {};
            },

            getMassForCell(dateKey, location) {
                const events = this.getEventsForDay(dateKey);
                const found = events.find(e => this.parseTitle(e.title).location.toLowerCase() == location.toLowerCase());
                return found;
            },

            getOrdinalSunday(dateKey) {
                if (!dateKey) return "";
                const d = new Date(dateKey);
                const start = new Date(d.getFullYear(), 0, 1);
                const week = Math.ceil((((d - start) / 86400000) + start.getDay() + 1) / 7);
                return week + "ème Dimanche du Temps Ordinaire";
            },

            addEvent(start_date) {
                this.events.push({
                    id: 0,
                    title: "Messe à ",
                    start_date,
                });
            },

            needsCelebrant(event) {
                return !!event.title.match(/^(Messe|Célébration|Confession)s?\b/);
            },
        };
        data = Alpine.reactive(data);
        fetch("/api/celebrants/").then(r => r.json()).then(e => data.celebrants = e);
        Alpine.effect(() => {
            data.events = null;
            let start = data.currentStartDate;
            if (!start) return;
            let end = new Date(start);
            end.setDate(end.getDate() + 8);
            getPersistentData("/api/dates/", {
                parameters: "?start=" + start.toISOString().split("T")[0] + "&end=" + end.toISOString().split("T")[0],
                defaultsIn: "event_details",
            }).then(e => data.events = e);
        });
        return data;
    });
});
