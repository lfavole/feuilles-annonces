function addMessage(content, severity) {
    var messageList = document.querySelector("main.content > ul.messagelist");

    if(!messageList) {
        messageList = document.createElement("ul");
        messageList.className = "messagelist";
        var main = document.querySelector("main.content");
        main.insertBefore(messageList, main.firstChild);
    }

    var message = document.createElement("li");
    message.className = severity;
    message.textContent = content;
    messageList.appendChild(message);
    return message;
}


django.jQuery(function() {
    var addDatesForm = document.querySelector("form.add-dates-form");
    if(!addDatesForm) return;

    var pendingAdded = 0;
    var pendingAddedMsg;

    addDatesForm.querySelector("tr:last-of-type").remove();
    addDatesForm.querySelectorAll("tr").forEach(function(p) {
        var input = p.querySelector("input");
        input.style.display = "none";
        var button = document.createElement("input");
        button.type = "button";
        button.value = "Add";
        button.addEventListener("click", async function() {
            if(button.disabled) return;
            var fd = new FormData(addDatesForm);
            addDatesForm.querySelectorAll("p input").forEach(e => fd.delete(e.name));
            fd.append(input.name, "on");
            button.value = "Adding...";
            button.disabled = true;
                try {
                var resp = await fetch(
                    addDatesForm.action,
                    {
                        method: "POST",
                        headers: {Accept: "application/json"},
                        body: fd,
                    },
                );
                var data = await resp.json();
            } catch(e) {
                var data = {};
            }
            if(!data.success) {
                button.value = "Add";
                button.disabled = false;
                addMessage("Could not add event.", "error");
                return;
            }
            pendingAdded++;
            pendingAddedMsg?.remove();
            pendingAddedMsg = addMessage(
                interpolate(
                    ngettext(
                        "%s event was added. Please reload the page to see it.",
                        "%s events were added. Please reload the page to see them.",
                        pendingAdded,
                    ),
                    [pendingAdded + ""],
                ),
                "warning",
            );
            p.remove();
            if(data.msg) alert(data.msg);
        })
        p.append(button);
    });
});
