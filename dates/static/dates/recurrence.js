document.addEventListener("DOMContentLoaded", async function() {
    var form = document.querySelector("#content-main form");
    var startDateInput = form.start_date;
    var endDateInput = form.end_date;
    if(!startDateInput || !endDateInput) return;
    var firstEndDatePlaceholder = endDateInput.placeholder;
    function addEndDatePlaceholder() {
        if(endDateInput.value.length) {
            endDateInput.placeholder = firstEndDatePlaceholder;
            return;
        }
        var date = startDateInput.value.strptime(get_format("DATE_INPUT_FORMATS")[0]);
        if(isNaN(date)) {
            endDateInput.placeholder = firstEndDatePlaceholder;
            return;
        }
        endDateInput.placeholder = date.strftime(get_format("DATE_INPUT_FORMATS")[0]);
    }
    startDateInput.addEventListener("change", addEndDatePlaceholder);
    startDateInput.addEventListener("keyup", addEndDatePlaceholder);
    addEndDatePlaceholder();
});

document.addEventListener("DOMContentLoaded", async function() {
    var form = document.querySelector("#content-main form");
    var startTimeInput = form.start_time;
    var endTimeInput = form._end_time;
    if(!startTimeInput || !endTimeInput) return;
    var firstEndTimePlaceholder = endTimeInput.placeholder;
    function addEndTimePlaceholder() {
        if(endTimeInput.value.length) {
            endTimeInput.placeholder = firstEndTimePlaceholder;
            return;
        }
        var match = startTimeInput.value.match(/^(\d+):(\d+)(?::(\d+))$/);
        if(!match) {
            endTimeInput.placeholder = firstEndTimePlaceholder;
            return;
        }
        var startTime = new Date(1970, 1, 1, +match[1], +match[2], +match[3]);
        var endTime = new Date(startTime);
        endTime.setHours(startTime.getHours() + 1);
        endTimeInput.placeholder = endTime.strftime(get_format("TIME_INPUT_FORMATS")[0]);
    }
    startTimeInput.addEventListener("change", addEndTimePlaceholder);
    startTimeInput.addEventListener("keyup", addEndTimePlaceholder);
    addEndTimePlaceholder();
});

document.addEventListener("DOMContentLoaded", async function() {
    const occurrencesList = document.getElementById("occurrences-list");
    const errorsContainer = document.getElementById("errors");
    const errorsList = document.getElementById("errors-list");
    var form = document.querySelector("#content-main form");

    function getFieldName(field) {
        return form[field]?.previousElementSibling?.textContent?.replace(/:$/, "")?.trim() || field;
    }

    function displayErrors(errors) {
        errorsList.innerHTML = "";
        if(!errors) {
            errorsContainer.style.display = "none";
            occurrencesList.style.display = "";
            return;
        }
        errorsContainer.style.display = "";
        occurrencesList.style.display = "none";
        if(errors?.constructor != Object)
            errors = {__all__: [{message: errors}]};

        for(var [field, errors] of Object.entries(errors)) {
            for(var error of errors) {
                var li = document.createElement("li");
                li.textContent = (field == "__all__" ? "" : getFieldName(field) + " : ") + error.message;
                errorsList.appendChild(li);
            }
        }
    }

    var updating = true;
    async function updateOccurrences() {
        if(updating) return;
        updating = true;
        try {
            var response = await fetch("../../get_occurrences", {
                method: "POST",
                body: new FormData(form),
            });
            var data = await response.json();
        } catch(e) {
            displayErrors(e);
            return;
        } finally {
            updating = false;
        }
        if(data.invalid) {
            displayErrors(data.errors);
            return;
        }
        displayErrors();
        while(occurrencesList.firstChild)
            occurrencesList.firstChild.remove();
        data.occurrences.forEach(function(occurrence) {
            // var start = occurrence.start || occurrence[0];
            // var end = occurrence.end || occurrence[1];
            // var name = occurrence.name;

            // const DATE_FORMAT = "%A %d %B %Y";
            // const TIME_FORMAT = "%H:%M:%S";

            // var formattedStart = [new Date(start).strftime(DATE_FORMAT)];
            // var formattedEnd = [new Date(end).strftime(DATE_FORMAT)];
            // if(start?.includes("T"))
            //     formattedStart.push(new Date(start).strftime(TIME_FORMAT));
            // if(end?.includes("T"))
            //     formattedEnd.push(new Date(end).strftime(TIME_FORMAT));

            const li = document.createElement("li");
            // li.textContent = (
            //     formattedStart[0]
            //     + (formattedEnd[0] == formattedStart[0] ? "" : " - " + formattedEnd[0])
            //     + (formattedStart[1] && formattedEnd[1] ? " " + formattedStart[1] + " - " + formattedEnd[1] : "")
            //     + (name ? " - " + name : "")
            // );
            li.innerHTML = occurrence;  // occurrence may contain superscript ordinals e.g. 1<sup>er</sup>
            occurrencesList.appendChild(li);
        });
        if(!data.ended) {
            const li = document.createElement("li");
            li.textContent = "...";
            occurrencesList.appendChild(li);
        }
    }

    // Écouteurs d'événements pour les champs de récurrence, de date de début et de date de fin
    form.addEventListener("change", updateOccurrences);

    updating = false;
    await updateOccurrences();

    if(!window.recurrence) return;

    recurrence.widget.Widget.prototype.update = (function(oldUpdate) {
        return function() {
            var ret = oldUpdate.apply(this, arguments);
            updateOccurrences();
            return ret;
        }
    })(recurrence.widget.Widget.prototype.update);
});
