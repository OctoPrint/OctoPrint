/**
 * User: hudbrog (hudbrog@gmail.com)
 * Date: 10/24/12
 * Time: 12:18 PM
 */

    var gcode;
    var firstReport;
    var toolOffsets = [
        {x: 0, y: 0}
    ];
    var z_heights = {};
    var model = [];
    var max = {x: undefined, y: undefined, z: undefined};
    var min = {x: undefined, y: undefined, z: undefined};
    var modelSize = {x: undefined, y: undefined, z: undefined};
    var filamentByLayer = {};
    var totalFilament = [0];
    var printTime = 0;
    var printTimeByLayer = {};
    var layerHeight = 0;
    var layerCnt = 0;
    var speeds = {extrude: [], retract: [], move: []};
    var speedsByLayer = {extrude: {}, retract: {}, move: {}};

    var sendLayerToParent = function(layerNum, z, progress){
        self.postMessage({
            "cmd": "returnLayer",
            "msg": {
                cmds: model[layerNum],
                layerNum: layerNum,
                zHeightObject: {zValue: z, layer: z_heights[z]},
                isEmpty: false,
                progress: progress
            }
        });
    };

    var sendMultiLayerToParent = function(layerNum, z, progress){
        var tmpModel = [];
        var tmpZHeight = {};

        for(var i=0;i<layerNum.length;i++){
            tmpModel[layerNum[i]] = model[layerNum[i]];
            tmpZHeight[layerNum[i]] = z_heights[z[i]];
        }

        self.postMessage({
            "cmd": "returnMultiLayer",
            "msg": {
                model: tmpModel,
                layerNum: layerNum,
                zHeightObject: {zValue: z, layer: tmpZHeight},
                isEmpty: false,
                progress: progress
            }
        });
    };


    var sendSizeProgress = function(progress){
        self.postMessage({
            "cmd": "analyzeProgress",
            "msg": {
                progress: progress,
                printTime: printTime
            }
        });
    };

    var sendAnalyzeDone = function(){
        self.postMessage({
            "cmd": "analyzeDone",
            "msg": {
                max: max,
                min: min,
                modelSize: modelSize,
                totalFilament: totalFilament,
                filamentByLayer: filamentByLayer,
                printTime: printTime,
                layerHeight: layerHeight,
                layerCnt: layerCnt,
                layerTotal: model.length,
                speeds: speeds,
                speedsByLayer: speedsByLayer,
                printTimeByLayer: printTimeByLayer
            }
        });
    };

    var purgeLayers = function () {
        var purge = true;
        for (var i = 0; i < model.length; i++) {
            purge = true;
            if (!model[i]) {
                purge = true;
            } else {
                for (var j = 0; j < model[i].length; j++) {
                    if (model[i][j].extrude)purge = false;
                }
            }
            if (!purge) {
                layerCnt += 1;
            }
        }
    };


    var analyzeModel = function() {
        var tmp1 = 0, tmp2 = 0;
        var speedIndex = 0;
        var type;
        var printTimeAdd = 0;

        for (var i = 0; i < model.length; i++) {
            var cmds = model[i];
            if(!cmds) continue;

            for (var j = 0; j < cmds.length; j++) {
                var tool = cmds[j].tool;

                var x_ok = false;
                var y_ok = false;

                if (typeof(cmds[j].x) !== 'undefined'
                        && typeof(cmds[j].prevX) !== 'undefined'
                        && typeof(cmds[j].extrude) !== 'undefined'
                        && cmds[j].extrude
                        && !isNaN(cmds[j].x)) {
                    var x = cmds[j].x;
                    max.x = max.x !== undefined ? Math.max(max.x, x) : x;
                    min.x = min.x !== undefined ? Math.min(min.x, x) : x;

                    x_ok = true;
                }

                if (typeof(cmds[j].y) !== 'undefined'
                        && typeof(cmds[j].prevY) !== 'undefined'
                        && typeof(cmds[j].extrude) !== 'undefined'
                        && cmds[j].extrude
                        && !isNaN(cmds[j].y)){
                    var y = cmds[j].y;

                    max.y = max.y !== undefined ? Math.max(max.y, y) : y;
                    min.y = min.y !== undefined ? Math.min(min.y, y) : y;

                    y_ok = true;
                }

                if (typeof(cmds[j].prevZ) !== 'undefined'
                        && typeof(cmds[j].extrude) !== 'undefined'
                        && cmds[j].extrude
                        && !isNaN(cmds[j].prevZ)) {
                    var z = cmds[j].prevZ;
                    max.z = max.z !== undefined ? Math.max(max.z, z) : z;
                    min.z = min.z !== undefined ? Math.min(min.z, z) : z;
                }

                if (!totalFilament[tool]) totalFilament[tool] = 0;
                if (!filamentByLayer[cmds[j].prevZ]) filamentByLayer[cmds[j].prevZ] = [0];
                if (!filamentByLayer[cmds[j].prevZ][tool]) filamentByLayer[cmds[j].prevZ][tool] = 0;
                if (cmds[j].extrusion) {
                    totalFilament[tool] += cmds[j].extrusion;
                    filamentByLayer[cmds[j].prevZ][tool] += cmds[j].extrusion;
                }

                var diffX = cmds[j].x - cmds[j].prevX;
                var diffY = cmds[j].y - cmds[j].prevY;
                if (x_ok && y_ok) {
                    printTimeAdd = Math.sqrt(diffX * diffX + diffY * diffY) / (cmds[j].speed / 60);
                } else if (cmds[j].retract === 0 && cmds[j].extrusion !== 0) {
                    tmp1 = Math.sqrt(diffX * diffX + diffY * diffY) / (cmds[j].speed / 60);
                    tmp2 = Math.abs(cmds[j].extrusion / (cmds[j].speed / 60));
                    printTimeAdd = Math.max(tmp1, tmp2);
                } else if (cmds[j].retract !== 0) {
                    printTimeAdd = Math.abs(cmds[j].extrusion / (cmds[j].speed/60));
                }

                printTime += printTimeAdd;
                if (typeof(printTimeByLayer[cmds[j].prevZ]) === 'undefined') {
                    printTimeByLayer[cmds[j].prevZ] = 0;
                }
                printTimeByLayer[cmds[j].prevZ] += printTimeAdd;

                if (cmds[j].extrude && cmds[j].retract === 0){
                    type = 'extrude';
                } else if (cmds[j].retract !== 0) {
                    type = 'retract';
                } else if (!cmds[j].extrude && cmds[j].retract === 0) {
                    type = 'move';
                } else {
                    self.postMessage({cmd: 'unknown type of move'});
                    type = 'unknown';
                }

                speedIndex = speeds[type].indexOf(cmds[j].speed);
                if (speedIndex === -1) {
                    speeds[type].push(cmds[j].speed);
                    speedIndex = speeds[type].indexOf(cmds[j].speed);
                }
                if (typeof(speedsByLayer[type][cmds[j].prevZ]) === 'undefined'){
                    speedsByLayer[type][cmds[j].prevZ] = [];
                }
                if (speedsByLayer[type][cmds[j].prevZ].indexOf(cmds[j].speed) === -1){
                    speedsByLayer[type][cmds[j].prevZ][speedIndex] = cmds[j].speed;
                }

            }
            sendSizeProgress(i / model.length * 100);

        }
        purgeLayers();

        modelSize.x = Math.abs(max.x - min.x);
        modelSize.y = Math.abs(max.y - min.y);
        modelSize.z = Math.abs(max.z - min.z);
        layerHeight = (max.z-min.z) / (layerCnt - 1);

        sendAnalyzeDone();
    };

    var doParse = function(){
        var argChar, numSlice;
        var sendLayer = undefined;
        var sendLayerZ = 0;
        var sendMultiLayer = [];
        var sendMultiLayerZ = [];
        var lastSend = 0;

        var layer = 0;
        var x, y, z = 0;
        var prevX = 0, prevY = 0, prevZ = 0;
        var f, lastF = 4000;
        var extrude = false, extrudeRelative = false, retract = 0;
        var positionRelative = false;

        var dcExtrude=false;
        var assumeNonDC = false;

        var tool = 0;
        var prev_extrude = [{a: 0, b: 0, c: 0, e: 0, abs: 0}];
        var prev_retract = [0];
        var offset = toolOffsets[0];

        model = [];
        for (var i=0; i < gcode.length; i++) {
            x = undefined;
            y = undefined;
            z = undefined;
            retract = 0;

            var line = gcode[i].line;
            var percentage = gcode[i].percentage;

            extrude=false;
            line = line.split(/[\(;]/)[0];

            var addToModel = false;
            var move = false;

            var log = false;

            if (/^(?:G0|G1)\s/i.test(line)) {
                var args = line.split(/\s/);

                for (var j = 0; j < args.length; j++) {
                    switch(argChar = args[j].charAt(0).toLowerCase()){
                        case 'x':
                            if (positionRelative) {
                                x = prevX + Number(args[j].slice(1)) + offset.x;
                            } else {
                                x = Number(args[j].slice(1)) + offset.x;
                            }

                            break;

                        case 'y':
                            if (positionRelative) {
                                y = prevY + Number(args[j].slice(1)) + offset.y;
                            } else {
                                y = Number(args[j].slice(1)) + offset.y;
                            }

                            break;

                        case 'z':
                            if (positionRelative) {
                                z = prevZ + Number(args[j].slice(1));
                            } else {
                                z = Number(args[j].slice(1));
                            }

                            break;

                        case 'e':
                        case 'a':
                        case 'b':
                        case 'c':
                            assumeNonDC = true;
                            numSlice = Number(args[j].slice(1));

                            if (!extrudeRelative) {
                                // absolute extrusion positioning
                                prev_extrude[tool]["abs"] = numSlice - prev_extrude[tool][argChar];
                                prev_extrude[tool][argChar] = numSlice;
                            } else {
                                prev_extrude[tool]["abs"] = numSlice;
                                prev_extrude[tool][argChar] += numSlice;
                            }

                            extrude = prev_extrude[tool]["abs"] > 0;
                            if (prev_extrude[tool]["abs"] < 0) {
                                prev_retract[tool] = -1;
                                retract = -1;
                            } else if (prev_extrude[tool]["abs"] == 0) {
                                retract = 0;
                            } else if (prev_extrude[tool]["abs"] > 0 && prev_retract[tool] < 0) {
                                prev_retract[tool] = 0;
                                retract = 1;
                            } else {
                                retract = 0;
                            }

                            break;

                        case 'f':
                            numSlice = parseFloat(args[j].slice(1));
                            lastF = numSlice;
                            break;
                    }
                }

                if (dcExtrude && !assumeNonDC) {
                    extrude = true;
                    prev_extrude[tool]["abs"] = Math.sqrt((prevX - x) * (prevX - x) + (prevY - y) * (prevY - y));
                }

                if (typeof(x) !== 'undefined' || typeof(y) !== 'undefined' || typeof(z) !== 'undefined' || retract != 0) {
                    addToModel = true;
                    move = true;
                }
            } else if (/^(?:M82)/i.test(line)) {
                extrudeRelative = false;
            } else if (/^(?:G91)/i.test(line)) {
                positionRelative = true;
                extrudeRelative = true;
            } else if (/^(?:G90)/i.test(line)) {
                positionRelative = false;
                extrudeRelative = false;
            } else if (/^(?:M83)/i.test(line)) {
                extrudeRelative = true;
            } else if (/^(?:M101)/i.test(line)) {
                dcExtrude = true;
            } else if (/^(?:M103)/i.test(line)) {
                dcExtrude = false;
            } else if (/^(?:G92)/i.test(line)) {
                var args = line.split(/\s/);

                for (var j=0; j < args.length; j++) {
                    if (!args[j]) continue;

                    if (args.length == 1) {
                        // G92 without coordinates => reset all axes to 0
                        x = 0;
                        y = 0;
                        z = 0;
                        prev_extrude[tool]["e"] = 0;
                        prev_extrude[tool]["a"] = 0;
                        prev_extrude[tool]["b"] = 0;
                        prev_extrude[tool]["c"] = 0;
                    } else {
                        switch (argChar = args[j].charAt(0).toLowerCase()) {
                            case 'x':
                                x = Number(args[j].slice(1)) + offset.x;
                                break;

                            case 'y':
                                y = Number(args[j].slice(1)) + offset.y;
                                break;

                            case 'z':
                                z = Number(args[j].slice(1));
                                prevZ = z;
                                break;

                            case 'e':
                            case 'a':
                            case 'b':
                            case 'c':
                                numSlice = Number(args[j].slice(1));
                                if(!extrudeRelative)
                                    prev_extrude[tool][argChar] = 0;
                                else {
                                    prev_extrude[tool][argChar] = numSlice;
                                }
                                break;
                        }
                    }
                }

                if (typeof(x) !== 'undefined' || typeof(y) !== 'undefined' || typeof(z) !== 'undefined') {
                    addToModel = true;
                    move = false;
                }

            } else if (/^(?:G28)/i.test(line)) {
                var args = line.split(/\s/);

                if (args.length == 1) {
                    // G28 with no arguments => home all axis
                    x = 0;
                    y = 0;
                    z = 0;
                } else {
                    for(j = 0; j < args.length; j++){
                        switch(argChar = args[j].charAt(0).toLowerCase()){
                            case 'x':
                                x = 0;
                                break;
                            case 'y':
                                y = 0;
                                break;
                            case 'z':
                                z = 0;
                                break;
                            default:
                                break;
                        }
                    }
                }

                // if it's the first layer and G28 was without z
                if (layer == 0 && typeof(z) === 'undefined') {
                    z = 0;
                }

                if (typeof(x) !== 'undefined' || typeof(y) !== 'undefined' || typeof(z) !== 'undefined' || retract != 0) {
                    addToModel = true;
                    move = true;
                }
            } else if (/^(?:T\d+)/i.test(line)) {
                tool = Number(line.split(/\s/)[0].slice(1));
                if (!prev_extrude[tool]) prev_extrude[tool] = {a: 0, b: 0, c: 0, e: 0, abs: 0};
                if (!prev_retract[tool]) prev_retract[tool] = 0;

                offset = toolOffsets[tool];
                if (!offset) offset = {x: 0, y: 0};
            }

            if (typeof(z) !== 'undefined' && z != prevZ) {
                if (z_heights[z]) {
                    layer = z_heights[z];
                } else {
                    layer = model.length;
                    z_heights[z] = layer;
                }

                sendLayer = layer;
                sendLayerZ = z;
                prevZ = z;
            } else if (typeof(z) == 'undefined' && typeof(prevZ) != 'undefined') {
                if (z_heights.hasOwnProperty(prevZ)) {
                    layer = z_heights[prevZ];
                } else {
                    layer = model.length;
                    z_heights[prevZ] = layer;
                }
            }

            if (addToModel) {
                if (!model[layer]) model[layer] = [];
                model[layer].push({
                    x: x,
                    y: y,
                    z: z,
                    extrude: extrude,
                    retract: retract,
                    noMove: !move,
                    extrusion: (extrude || retract) && prev_extrude[tool]["abs"] ? prev_extrude[tool]["abs"] : 0,
                    prevX: prevX,
                    prevY: prevY,
                    prevZ: prevZ,
                    speed: lastF,
                    gcodeLine: i,
                    percentage: percentage,
                    tool: tool
                });
            }

            if (move) {
                if (typeof(x) !== 'undefined') prevX = x;
                if (typeof(y) !== 'undefined') prevY = y;
            }

            if (typeof(sendLayer) !== "undefined") {
                if (i - lastSend > gcode.length*0.02 && sendMultiLayer.length != 0){
                    lastSend = i;
                    sendMultiLayerToParent(sendMultiLayer, sendMultiLayerZ, i / gcode.length * 100);
                    sendMultiLayer = [];
                    sendMultiLayerZ = [];
                }
                sendMultiLayer[sendMultiLayer.length] = sendLayer;
                sendMultiLayerZ[sendMultiLayerZ.length] = sendLayerZ;
                sendLayer = undefined;
                sendLayerZ = undefined;
            }
        }
        sendMultiLayerToParent(sendMultiLayer, sendMultiLayerZ, i / gcode.length*100);
    };


    var parseGCode = function(message){
        gcode = message.gcode;
        firstReport = message.options.firstReport;
        toolOffsets = message.options.toolOffsets;
        if (!toolOffsets || toolOffsets.length == 0) toolOffsets = [{x: 0, y: 0}]

        doParse();
        gcode = [];
        self.postMessage({
            "cmd": "returnModel",
            "msg": {}
        });
    };

    var runAnalyze = function(message){
        analyzeModel();
        model = [];
        z_heights = [];
        gcode = undefined;
        firstReport = undefined;
        z_heights = {};
        model = [];
        max = {x: undefined, y: undefined, z: undefined};
        min = {x: undefined, y: undefined, z: undefined};
        modelSize = {x: undefined, y: undefined, z: undefined};
        filamentByLayer = {};
        totalFilament=0;
        printTime=0;
        printTimeByLayer = {};
        layerHeight=0;
        layerCnt = 0;
        speeds = {extrude: [], retract: [], move: []};
        speedsByLayer = {extrude: {}, retract: {}, move: {}};
    };

    var setOption = function(options){
        for(var opt in options){
            gCodeOptions[opt] = options[opt];
        }
    };

onmessage = function (e){
    var data = e.data;
    // for some reason firefox doesn't garbage collect when something inside closures is deleted, so we delete and recreate whole object eaech time
    switch (data.cmd) {
        case 'parseGCode':
            parseGCode(data.msg);
            break;
        case 'setOption':
            setOption(data.msg);
            break;
        case 'analyzeModel':
            runAnalyze(data.msg);
            break;

        default:
            self.postMessage('Unknown command: ' + data.msg);
    }

};
