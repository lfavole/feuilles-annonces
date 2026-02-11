function songEditor() {
    const VERSE_NUMBER_RE = /^(\d+)[.)-\s]*/m;
    const CHORUS_RE = /^r\w*\s*[.)/-\s]*\b/im;
    function trimLines(text) {
        return text.replace(/^[\f\r\t\v ]+|[\f\r\t\v ]+$/gm, "").trim();
    }
    return {
        _raw: "",
        normalizationTimer: null,
        chorusAfter: false,
        chorus: "",
        verses: [],
        editingRaw: false,
        init() {
            this.$nextTick(() => {
                this.raw = this.generateRaw();
            });
        },
        get raw() {
            return this._raw;
        },
        set raw(val) {
            this._raw = val;

            try {
                this.editingRaw = true;
                const parsed = this.parse();
                this.chorus = parsed.chorus;
                this.verses = parsed.verses;
                this.isAfter = parsed.isAfter;
            } finally {
                this.editingRaw = false;
            }
        },
        handleInput() {
            if (this.normalizationTimer)
                clearTimeout(this.normalizationTimer);
            this.normalizationTimer = setTimeout(() => {
                this.autoNormalize();
            }, 3000);
        },
        autoNormalize() {
            this._raw = this.generateRaw(this.parse());
        },
        get isNormalized() {
            return this.normalize(this.raw) == trimLines(this.raw).replace(/[\f\r\t\v ]+/g, " ");
        },
        get isCorrect() {
            return this.normalize(this.raw) == this.normalize(this.generateRaw(this.parse()));
        },
        normalize(text) {
            return (
                trimLines(text)
                .replace(/[\f\r\t\v ]+/g, " ")
                // .replace(/\s+/g, " ")
                .replace(/\n\n+/g, "\n\n")
                .replace(VERSE_NUMBER_RE, "$1. ")
                .replace(CHORUS_RE, "R/ ")
            );
        },
        parse() {
            const blocks = this.raw.split(/(?<!\s)\n[\f\r\t\v ]*\n/);
            let data = {
                chorus: "",
                verses: [],
                isAfter: false,
            };
            let verseAdded = false;
            blocks.forEach((block) => {
                const trimmed = trimLines(block);
                if (CHORUS_RE.test(trimmed)) {
                    data.chorus = trimmed.replace(CHORUS_RE, "");
                    data.isAfter = verseAdded;
                } else {
                    let text = trimmed.replace(VERSE_NUMBER_RE, "");
                    if (text) {
                        verseAdded = true;
                        data.verses.push(text);
                    }
                }
            });
            return data;
        },
        generateRaw(data) {
            data ||= this;
            let lines = [];
            if (!data.isAfter && data.chorus) {
                lines.push("R/ " + data.chorus);
            }
            data.verses.forEach((v, i) => {
                lines.push((i + 1) + ". " + v);
                if (data.isAfter && i === 0 && data.chorus) {
                    lines.push("R/ " + data.chorus);
                }
            });
            return lines.join("\n\n");
        },
       _isAfter: false,
        get isAfter() {
            return this._isAfter;
        },
        set isAfter(val) {
            this._isAfter = val;
            this.updateRaw({isAfter: val});
        },
       _chorus: "",
        get chorus() {
            return this._chorus;
        },
        set chorus(val) {
            this._chorus = val;
            this.updateRaw({chorus: val});
        },
        get verses() {
            return JSON.parse(this.versesJson || "[]");
        },
        set verses(val) {
            this.versesJson = JSON.stringify(val);
        },
       _versesJson: "",
        get versesJson() {
            return this._versesJson;
        },
        set versesJson(val) {
            this._versesJson = val;
            this.updateRaw({verses: this.verses});
        },
        updateRaw(overrides = {}) {
            if (this.editingRaw) return;
            const current = this.parse();
            this.raw = this.generateRaw({
                ...current,
                ...overrides
            });
        }
    };
}
