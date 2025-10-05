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
    var form = document.getElementById("recurrence_form");
    var fields = ["start_time", "_end_time", "recurrence"];

    function displayErrors(errors) {
        errorsList.innerHTML = "";
        if(!errors) {
            errorsContainer.style.display = "none";
            occurrencesList.style.display = "";
            return;
        }
        errorsContainer.style.display = "";
        occurrencesList.style.display = "none";
        if(!Array.isArray(errors))
            errors = {__all__: [{message: errors}]};

        for(var [field, errors] of Object.entries(data.errors)) {
            for(var error of errors) {
                var li = document.createElement("li");
                li.textContent = (field == "__all__" ? "" : field + " : ") + error.message;
                errorsList.appendChild(li);
            }
        }
    }

    var updating = true;
    async function updateOccurrences() {
        if(updating) return;
        updating = true;
        try {
            var response = await fetch(GET_OCCURRENCES_URL, {
                method: "POST",
                body: new FormData(form),
            });
        } catch(e) {
            displayErrors(e);
            return;
        } finally {
            updating = false;
        }
        var data = await response.json();
        if(data.invalid) {
            displayErrors(data.errors);
            return;
        }
        displayErrors();
        while(occurrencesList.firstChild)
            occurrencesList.firstChild.remove();
        data.occurrences.forEach(function(occurrence) {
            // const format = get_format(occurrence[0].includes("T") ? "DATETIME_INPUT_FORMATS" : "DATE_INPUT_FORMATS")[0];
            const format = "%A %d %B %Y" + (occurrence[0].includes("T") ? " %H:%M:%S" : "");

            const li = document.createElement("li");
            li.textContent = (
                new Date(occurrence[0]).strftime(format)
                + (occurrence[1] && occurrence[1] != occurrence[0] ? " - " + new Date(occurrence[1]).strftime(format) : "")
            );
            occurrencesList.appendChild(li);

            // const exceptionButton = document.createElement("input");
            // exceptionButton.type = "button";
            // exceptionButton.value = "×";
            // li.appendChild(exceptionButton);
            // exceptionButton.addEventListener("click", function() {
            //     var rec = recurrence.deserialize(form.recurrence.value);
            //     var date = new Date(occurrence[0]);
            //     date.setHours(0);
            //     date.setMinutes(0);
            //     date.setSeconds(0);
            //     rec.exdates.push(date);
            //     form.recurrence.value = rec.serialize();
            //     if(form.recurrence.previousElementSibling.classList.contains("recurrence-widget")) {
            //         form.recurrence.previousElementSibling.remove();
            //         form.recurrence.classList.remove("hidden");
            //         new recurrence.widget.Widget(form.recurrence.id, {});
            //     }
            //     updateOccurrences();
            // });
        });
        if(!data.ended) {
            const li = document.createElement("li");
            li.textContent = "...";
            occurrencesList.appendChild(li);
        }
    }

    // Écouteurs d'événements pour les champs de récurrence, de date de début et de date de fin
    for(var field of fields) {
        form[field].addEventListener("change", updateOccurrences);
    }
    recurrence.widget.Widget.prototype.update = (function(oldUpdate) {
        return function() {
            var ret = oldUpdate.apply(this, arguments);
            updateOccurrences();
            return ret;
        }
    })(recurrence.widget.Widget.prototype.update);
    updating = false;
    await updateOccurrences();
});
