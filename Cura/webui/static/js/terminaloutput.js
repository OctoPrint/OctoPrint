var terminaloutput = function() {

    var updateInterval = 1000;
    function update() {
        function onDataReceived(response) {
            var log = response.log;
            var output = '';
            for (var i = 0; i < log.length; i++) {
                output += log[i] + '<br>';
            }

            var container = $("#terminal-output");
            var autoscroll = (container.scrollTop() == container[0].scrollHeight - container.height);

            container.html(output);

            if (autoscroll) {
                container.scrollTop(container[0].scrollHeight - container.height())
            }
        }

        $.ajax({
            url: "/api/printer/log",
            type: 'GET',
            dataType: 'json',
            success: onDataReceived
        })

        setTimeout(update, updateInterval);
    }

    update();

    $("#terminal-send").click(function () {
        var command = $("#terminal-command").val();
        $.ajax({
            url: "/api/printer/command",
            type: 'POST',
            dataType: 'json',
            data: 'command=' + command,
            success: function(response) {
                // do nothing
            }
        })
    })

}

terminaloutput();