
var temperaturegraph = function() {

    var options = {
        yaxis: {
            min: 0,
            max: 310,
            ticks: 10
        },
        xaxis: {
            mode: "time"
        },
        legend: {
            noColumns: 4
        }
    };

    var updateInterval = 500;
    function update() {
        function onDataReceived(response) {
            var temps = response.temperatures;
            var data = [
                {label: "Actual", color: "#FF4040", data: temps.actual},
                {label: "Target", color: "#FFA0A0", data: temps.target},
                {label: "Bed Actual", color: "#4040FF", data: temps.actualBed},
                {label: "Bed Target", color: "#A0A0FF", data: temps.targetBed}
            ]
            $.plot($("#temperature-graph"), data, options);
        }

        $.ajax({
            url: "/api/printer/temperatures",
            method: 'GET',
            dataType: 'json',
            success: onDataReceived
        })

        setTimeout(update, updateInterval);
    }

    update();

}

temperaturegraph();