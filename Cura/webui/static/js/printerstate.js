var printerstate = function() {

    var updateInterval = 500;
    function update() {
        function onDataReceived(response) {
            $("#printer_state").text(response.state);
            $("#printer_temp").text(response.temp + " °C");
            $("#printer_bedTemp").text(response.bedTemp + " °C");

            if (response.job) {
                var currentLine = (response.job.line ? response.job.line : 0);
                var progress = currentLine * 100 / response.job.totalLines;
                $("#job_filament").text(response.job.filament);
                $("#job_estimatedPrintTime").text(response.job.estimatedPrintTime);
                $("#job_line").text((currentLine == 0 ? "-" : currentLine) + "/" + response.job.totalLines + " " + progress + "%");
                $("#job_height").text(response.job.currentZ);
                $("#job_printTime").text(response.job.printTime);
                $("#job_printTimeLeft").text(response.job.printTimeLeft);
                $("#job_progressBar").width(progress + "%");
            } else {
                $("#job_filament").text("-");
                $("#job_estimatedPrintTime").text("-");
                $("#job_line").text("-");
                $("#job_height").text("-");
                $("#job_printTime").text("-");
                $("#job_printTimeLefT").text("-");
                $("#job_progressBar").width("0%");
            }

            if (!response.closedOrError) {
                $("#printer_connect").click(function(){});
                $("#printer_connect").addClass("disabled");
            } else {
                $("#printer_connect").click(connect);
                $("#printer_connect").removeClass("disabled");
            }

            $("#job_print").click(function() {
                $.ajax({
                    url: "/api/printer/print",
                    type: 'POST',
                    dataType: 'json',
                    success: function(){}
                })
            })
            $("#job_pause").click(function() {
                $.ajax({
                    url: "/api/printer/pause",
                    type: 'POST',
                    dataType: 'json',
                    success: function(){}
                })
            })
            $("#job_cancel").click(function() {
                $.ajax({
                    url: "/api/printer/cancel",
                    type: 'POST',
                    dataType: 'json',
                    success: function(){}
                })
            })
        }

        $.ajax({
            url: "/api/printer",
            method: 'GET',
            dataType: 'json',
            success: onDataReceived
        });

        setTimeout(update, updateInterval);
    }

    function connect() {
        $.ajax({
            url: "/api/printer/connect",
            type: 'POST',
            dataType: 'json',
            success: function(response) {
                // do nothing
            }
        })
    }

    update();
}

printerstate();