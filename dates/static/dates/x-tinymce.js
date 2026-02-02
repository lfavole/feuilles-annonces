document.addEventListener("alpine:init", () => {
    Alpine.directive("tinymce", (el, { modifiers, expression }, { effect, cleanup }) => {
        if (expression) {
            Alpine.bind(el, {"x-model": expression});
            el.setAttribute("x-model", expression);
        }

        const inline = modifiers.includes("inline");

        tinymce.init({
            target: el,
            license_key: "gpl",
            language: "fr-FR",
            language_url: "/static/dates/fr_FR.js",
            inline: inline,
            toolbar: !inline,
            menubar: !inline,
            plugins: inline ? "lists link" : null,
            toolbar: inline ? "bold italic underline bullist numlist" : null,
            setup: (editor) => {
                let internalChange = false;

                // set initial content on init
                editor.on("init", () => {
                    // model -> editor: watch Alpine expression
                    // use evaluateLater to read the expression whenever Alpine triggers effects
                    effect(() => {
                        const current = el._x_model.get() ?? "";
                        if (internalChange) return;
                        if (editor.getContent() != current)
                            editor.setContent(current);
                    });
                });

                // editor -> model
                editor.on("change keyup", () => {
                    internalChange = true;
                    el._x_model.set(editor.getContent());
                    setTimeout(() => { internalChange = false; }, 0);
                });

                const applyDisabledState = () => {
                    editor.options.set("disabled", el.hasAttribute("disabled"));
                };

                applyDisabledState();

                const attrObserver = new MutationObserver(muts => {
                    for (const m of muts) {
                        if (m.type == "attributes" && m.attributeName == "disabled") {
                            applyDisabledState();
                            break;
                        }
                    }
                });
                attrObserver.observe(el, { attributes: true });

                cleanup(() => {
                    attrObserver.disconnect();
                    editor.destroy();
                });
            },
        });
    });
});
