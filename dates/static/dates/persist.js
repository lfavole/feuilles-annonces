async function getPersistentData(
    endpoint,
    {
        parameters = "",
        headers = {},
        ignoredProperties = [],
        defaultsIn = null,
    } = {},
) {
    // Récupération initiale des données
    const resp = await fetch(endpoint + parameters, { headers });
    let data = Alpine.reactive(await resp.json());

    function setDefaultsAndFix(item) {
        if (defaultsIn && item[defaultsIn]) {
            for (let key of Object.keys(item)) {
                if (key != "id" && (item[key] == null || item[key] == ""))
                    item[key] = item[defaultsIn][key];
            }
        }
        let itemsToEdit = [item];
        if (defaultsIn && item[defaultsIn])
            itemsToEdit.push(item[defaultsIn]);
        for (let itemToEdit of itemsToEdit) {
            itemToEdit.start_time = itemToEdit.start_time?.replace(/^(\d\d:\d\d):\d\d$/, "$1");
            itemToEdit.end_time = itemToEdit.end_time?.replace(/^(\d\d:\d\d):\d\d$/, "$1");
        }
    }

    function getDataForServer(item) {
        if (!defaultsIn || !item[defaultsIn]) return item;
        let ret = {};
        for (let key of Object.keys(item)) {
            if (key == defaultsIn)
                continue;
            if (key == "id" || !item[defaultsIn][key] || item[key] != item[defaultsIn][key])
                ret[key] = item[key];
            else
                ret[key] = key.includes("date") || key.includes("time") ? null : "";
        }
        return ret;
    }

    function getLastState(item) {
        let ret = {};
        for (let key of Object.keys(item)) {
            if (key == "_lastState")
                continue;
            if (key == defaultsIn) {
                ret[key] = item[key] && { id: item[key].id };
                continue;
            }
            if (defaultsIn && item[defaultsIn] && item[key] == item[defaultsIn][key])
                continue;
            ret[key] = item[key];
        }
        return JSON.stringify(Object.fromEntries(Object.entries(ret).sort()));
    }

    // Stockage pour le debounce et le suivi des suppressions
    const pendingSyncs = new Map();
    let previousIds;

    // Fonction de persistance universelle (POST, PATCH, DELETE)
    async function persistToServer(item, method = null) {
        const isNew = item.id == null;
        const url = isNew ? endpoint : `${endpoint}${item.id}/`;
        const fetchMethod = method || (isNew ? "POST" : "PATCH");

        try {
            const response = await fetch(url, {
                method: fetchMethod,
                headers: {
                    "X-CSRFToken": document.querySelector('input[name="csrfmiddlewaretoken"]').value,
                    "Content-Type": "application/json",
                    ...headers,
                },
                body: fetchMethod == "DELETE" ? null : JSON.stringify(
                    Object.fromEntries(
                        Object.entries(getDataForServer(item))
                        .filter(([k, v]) => k != "_lastState" && k != defaultsIn && !ignoredProperties.includes(k))
                    )
                ),
            });
            if (!response.ok) return;

            if (fetchMethod == "DELETE") {
                console.log(`[API] Supprimé du serveur : ${item.id}`);
                return;
            }

            const result = await response.json();
            if (isNew && result.id) {
                item.id = result.id;
                // On met à jour le set des IDs connus pour ne pas simuler une suppression
                previousIds.add(item.id);
            }
            // Marquer l'état comme synchronisé
            item._lastState = getLastState(item);
            console.log(`[API] Synchronisé : ${item.id}`);
        } catch (error) {
            console.error("[API] Erreur :", error);
        }
    }

    // Surveillance automatique (effet réactif)
    let working = false;
    Alpine.effect(() => {
        if (working) return;
        working = true;

        try {
            // On crée une empreinte du tableau pour détecter ajouts/suppressions
            const currentIds = new Set(data.map(item => item.id).filter(id => id > 0));

            // --- DETECTION DES SUPPRESSIONS ---
            if (previousIds != null) {
                for (let id of previousIds) {
                    if (!currentIds.has(id)) {
                        console.log(`[Sync] Détection suppression de l'ID : ${id}`);
                        persistToServer({ id }, "DELETE");
                    }
                }
            }
            previousIds = currentIds;

            // --- DETECTION DES MODIFICATIONS ET AJOUTS ---
            for (let item of data) {
                setDefaultsAndFix(item);
                const currentState = getLastState(item);

                // Si l'objet est nouveau (pas de _lastState) ou a changé
                if (item.id != null && item.id <= 0 || item._lastState != null && item._lastState != currentState) {
                    if (item.id <= 0)
                        item.id = null;
                    clearTimeout(pendingSyncs.get(item.id));
                    clearTimeout(pendingSyncs.get(item));
                    pendingSyncs.set(item.id || item, setTimeout(() => {
                        persistToServer(item);
                    }, 800));
                }
                item._lastState = currentState;
            }
        } finally {
            working = false;
        }
    });

    return data;
}
