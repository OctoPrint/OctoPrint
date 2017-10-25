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
var g90InfluencesExtruder = false;
var z_heights = {};
var model = [];
var max = {x: undefined, y: undefined, z: undefined};
var min = {x: undefined, y: undefined, z: undefined};
var boundingBox = {minX: undefined, maxX: undefined, minY: undefined, maxY: undefined, minZ: undefined, maxZ: undefined};
var modelSize = {x: undefined, y: undefined, z: undefined};
var bed = {x: undefined, y: undefined, r: undefined, circular: false, centeredOrigin: false};
var ignoreOutsideBed = false;
var filamentByLayer = {};
var totalFilament = [0];
var printTime = 0;
var printTimeByLayer = {};
var layerHeight = 0;
var layerCnt = 0;
var speeds = {extrude: [], retract: [], move: []};
var speedsByLayer = {extrude: {}, retract: {}, move: {}};

var sendLayerToParent = function (layerNum, z, progress) {
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

var sendMultiLayerToParent = function (layerNum, z, progress) {
    var tmpModel = [];
    var tmpZHeight = {};

    for (var i = 0; i < layerNum.length; i++) {
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


var sendSizeProgress = function (progress) {
    self.postMessage({
        "cmd": "analyzeProgress",
        "msg": {
            progress: progress,
            printTime: printTime
        }
    });
};

var sendAnalyzeDone = function () {
    self.postMessage({
        "cmd": "analyzeDone",
        "msg": {
            max: max,
            min: min,
            modelSize: modelSize,
            boundingBox: boundingBox,
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

var bedBounds = function() {
    if (!bed) {
        return {xMin: 0, xMax: 0, yMin: 0, yMax: 0};
    }

    var result;
    if (bed.circular) {
        result = {xMin: -bed.r, xMax: bed.r, yMin: -bed.r, yMax: bed.r};
    } else if (bed.centeredOrigin) {
        result = {xMin: -bed.x/2.0, xMax: bed.x/2.0, yMin: -bed.y/2.0, yMax: bed.y/2.0};
    } else {
        result = {xMin: 0, xMax: bed.x, yMin: 0, yMax: bed.y};
    }
    return result;
};

var withinBedBounds = function(x, y, bedBounds) {
    if (!ignoreOutsideBed) return true;

    var result = true;

    if (x !== undefined && !isNaN(x)) {
        result = result && (x >= bedBounds.xMin && x <= bedBounds.xMax);
    }
    if (y !== undefined && !isNaN(y)) {
        result = result && (y >= bedBounds.yMin && y <= bedBounds.yMax);
    }

    return result;
};

var analyzeModel = function () {
    var tmp1 = 0, tmp2 = 0;
    var speedIndex = 0;
    var type;
    var printTimeAdd = 0;

    var bounds = bedBounds();

    for (var i = 0; i < model.length; i++) {
        var cmds = model[i];
        if (!cmds) continue;

        for (var j = 0; j < cmds.length; j++) {
            var tool = cmds[j].tool;

            var retract = cmds[j].retract && cmds[j].retract > 0;
            var extrude = cmds[j].extrude && cmds[j].extrude > 0 && !retract;
            var move = cmds[j].x !== undefined || cmds[j].y !== undefined || cmds[j].z !== undefined;

            var prevInBounds = withinBedBounds(cmds[j].prevX, cmds[j].prevY, bounds);
            var inBounds = withinBedBounds(cmds[j].x === undefined ? cmds[j].prevX : cmds[j].x,
                                           cmds[j].y === undefined ? cmds[j].prevY : cmds[j].y,
                                           bounds);

            var recordX = function(x, inBounds) {
                if (x === undefined || isNaN(x)) return;

                max.x = max.x !== undefined ? Math.max(max.x, x) : x;
                min.x = min.x !== undefined ? Math.min(min.x, x) : x;

                if (inBounds) {
                    boundingBox.minX = boundingBox.minX !== undefined ? Math.min(boundingBox.minX, x): x;
                    boundingBox.maxX = boundingBox.maxX !== undefined ? Math.max(boundingBox.maxX, x): x;
                }
            };

            var recordY = function(y, inBounds) {
                if (y === undefined || isNaN(y)) return;

                max.y = max.y !== undefined ? Math.max(max.y, y) : y;
                min.y = min.y !== undefined ? Math.min(min.y, y) : y;

                if (inBounds) {
                    boundingBox.minY = boundingBox.minY !== undefined ? Math.min(boundingBox.minY, y): y;
                    boundingBox.maxY = boundingBox.maxY !== undefined ? Math.max(boundingBox.maxY, y): y;
                }
            };

            var recordZ = function(z) {
                if (z === undefined || isNaN(z)) return;

                max.z = max.z !== undefined ? Math.max(max.z, z) : z;
                min.z = min.z !== undefined ? Math.min(min.z, z) : z;

                boundingBox.minZ = min.z;
                boundingBox.maxZ = max.z;
            };

            if (move && extrude) {
                recordX(cmds[j].prevX, prevInBounds);
                recordX(cmds[j].x, inBounds);
                recordY(cmds[j].prevY, prevInBounds);
                recordY(cmds[j].y, inBounds);
                recordZ(cmds[j].prevZ);
                recordZ(cmds[j].z);
            }

            if (!totalFilament[tool]) totalFilament[tool] = 0;
            if (!filamentByLayer[cmds[j].prevZ]) filamentByLayer[cmds[j].prevZ] = [0];
            if (!filamentByLayer[cmds[j].prevZ][tool]) filamentByLayer[cmds[j].prevZ][tool] = 0;
            if (cmds[j].extrusion) {
                totalFilament[tool] += cmds[j].extrusion;
                filamentByLayer[cmds[j].prevZ][tool] += cmds[j].extrusion;
            }

            if (cmds[j].x !== undefined && !isNaN(cmds[j].x)
                    && cmds[j].y !== undefined && !isNaN(cmds[j].y)) {
                var diffX = cmds[j].x - cmds[j].prevX;
                var diffY = cmds[j].y - cmds[j].prevY;
                if (move) {
                    printTimeAdd = Math.sqrt(diffX * diffX + diffY * diffY) / (cmds[j].speed / 60);
                } else if (extrude) {
                    tmp1 = Math.sqrt(diffX * diffX + diffY * diffY) / (cmds[j].speed / 60);
                    tmp2 = Math.abs(cmds[j].extrusion / (cmds[j].speed / 60));
                    printTimeAdd = Math.max(tmp1, tmp2);
                } else if (retract) {
                    printTimeAdd = Math.abs(cmds[j].extrusion / (cmds[j].speed / 60));
                }
            } else {
                printTimeAdd = 0;
            }

            printTime += printTimeAdd;
            if (printTimeByLayer[cmds[j].prevZ] === undefined) {
                printTimeByLayer[cmds[j].prevZ] = 0;
            }
            printTimeByLayer[cmds[j].prevZ] += printTimeAdd;

            if (cmds[j].extrude && cmds[j].retract === 0) {
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
            if (typeof(speedsByLayer[type][cmds[j].prevZ]) === 'undefined') {
                speedsByLayer[type][cmds[j].prevZ] = [];
            }
            if (speedsByLayer[type][cmds[j].prevZ].indexOf(cmds[j].speed) === -1) {
                speedsByLayer[type][cmds[j].prevZ][speedIndex] = cmds[j].speed;
            }

        }
        sendSizeProgress(i / model.length * 100);

    }
    purgeLayers();

    modelSize.x = Math.abs(max.x - min.x);
    modelSize.y = Math.abs(max.y - min.y);
    modelSize.z = Math.abs(max.z - min.z);
    layerHeight = (max.z - min.z) / (layerCnt - 1);

    sendAnalyzeDone();
};

var doParse = function () {
    var argChar, numSlice;
    var sendLayer = undefined;
    var sendLayerZ = 0;
    var sendMultiLayer = [];
    var sendMultiLayerZ = [];
    var lastSend = 0;

    var layer = 0;
    var x, y, z = 0;
    var center_i, center_j, direction;
    var prevX = 0, prevY = 0, prevZ = 0;
    var f, lastF = 4000;
    var extrude = false, relativeE = false, retract = 0;
    var relativeMode = false;
    var zLift = false;
    var zLiftZ = undefined;
    var zLiftMoves = [];

    var dcExtrude = false;
    var assumeNonDC = false;

    var tool = 0;
    var prev_extrude = [{a: 0, b: 0, c: 0, e: 0, abs: 0}];
    var prev_retract = [0];

    // we keep track of our active toolOffset here so that our visualization lines up - if we didn't
    // offset the coordinates from the GCODE file with the tool offset, stuff would look wonky since our
    // visualizer doesn't actually have a physical offset ;)
    var activeToolOffset = toolOffsets[0];

    var i, j, args;

    model = [];
    for (i = 0; i < gcode.length; i++) {
        x = undefined;
        y = undefined;
        z = undefined;
        retract = 0;
        center_i = undefined;
        center_j = undefined;
        direction = undefined;

        var line = gcode[i].line;
        var percentage = gcode[i].percentage;

        extrude = false;
        line = line.split(/[\(;]/)[0];

        if (!line || line.trim() === "") {
            // empty line, skip entirely
            continue;
        }

        var addToModel = false;
        var move = false;

        var log = false;

        if (/^(?:G0|G1|G2|G3)\s/i.test(line)) {
            args = line.split(/\s/);

            for (j = 0; j < args.length; j++) {
                switch (argChar = args[j].charAt(0).toLowerCase()) {
                    case 'x':
                        if (relativeMode) {
                            x = prevX + Number(args[j].slice(1)) + activeToolOffset.x;
                        } else {
                            x = Number(args[j].slice(1)) + activeToolOffset.x;
                        }

                        break;

                    case 'y':
                        if (relativeMode) {
                            y = prevY + Number(args[j].slice(1)) + activeToolOffset.y;
                        } else {
                            y = Number(args[j].slice(1)) + activeToolOffset.y;
                        }

                        break;

                    case 'z':
                        if (relativeMode) {
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

                        if (relativeMode || relativeE) {
                            prev_extrude[tool]["abs"] = numSlice;
                            prev_extrude[tool][argChar] += numSlice;
                        } else {
                            // absolute extrusion positioning
                            prev_extrude[tool]["abs"] = numSlice - prev_extrude[tool][argChar];
                            prev_extrude[tool][argChar] = numSlice;
                        }

                        extrude = prev_extrude[tool]["abs"] > 0;
                        if (prev_extrude[tool]["abs"] < 0) {
                            prev_retract[tool] = -1;
                            retract = -1;
                        } else if (prev_extrude[tool]["abs"] === 0) {
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
                    case 'i':
                        center_i = Number(args[j].slice(1));
                        break;
                    case 'j':
                        center_j = Number(args[j].slice(1));
                        break;
                    case 'g':
                        if(args[j].charAt(1).toLowerCase() === '2')
                            direction=1;
                        if(args[j].charAt(1).toLowerCase() === '3')
                            direction=-1;
                        break;
                }
            }

            if (dcExtrude && !assumeNonDC) {
                extrude = true;
                prev_extrude[tool]["abs"] = Math.sqrt((prevX - x) * (prevX - x) + (prevY - y) * (prevY - y));
            }

            if (typeof(x) !== 'undefined' || typeof(y) !== 'undefined' || typeof(z) !== 'undefined' || retract !== 0) {
                addToModel = true;
                move = true;
            }
        } else if (/^(?:M82)/i.test(line)) {
            relativeE = false;
        } else if (/^(?:G91)/i.test(line)) {
            relativeMode = true;
            if (g90InfluencesExtruder) {
                relativeE = true;
            }
        } else if (/^(?:G90)/i.test(line)) {
            relativeMode = false;
            if (g90InfluencesExtruder) {
                relativeE = false;
            }
        } else if (/^(?:M83)/i.test(line)) {
            relativeE = true;
        } else if (/^(?:M101)/i.test(line)) {
            dcExtrude = true;
        } else if (/^(?:M103)/i.test(line)) {
            dcExtrude = false;
        } else if (/^(?:G92)/i.test(line)) {
            args = line.split(/\s/);

            for (j = 0; j < args.length; j++) {
                if (!args[j]) continue;

                if (args.length === 1) {
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
                            x = Number(args[j].slice(1)) + activeToolOffset.x;
                            break;

                        case 'y':
                            y = Number(args[j].slice(1)) + activeToolOffset.y;
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
                            if (relativeMode || relativeE) {
                                prev_extrude[tool][argChar] = numSlice;
                            } else {
                                prev_extrude[tool][argChar] = 0;
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
            args = line.split(/\s/);

            if (args.length === 1) {
                // G28 with no arguments => home all axis
                x = 0;
                y = 0;
                z = 0;
            } else {
                for (j = 0; j < args.length; j++) {
                    switch (argChar = args[j].charAt(0).toLowerCase()) {
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
            if (layer === 0 && typeof(z) === 'undefined') {
                z = 0;
            }

            if (typeof(x) !== 'undefined' || typeof(y) !== 'undefined' || typeof(z) !== 'undefined' || retract !== 0) {
                addToModel = true;
                move = true;
            }
        } else if (/^(?:T\d+)/i.test(line)) {
            tool = Number(line.split(/\s/)[0].slice(1));
            if (!prev_extrude[tool]) prev_extrude[tool] = {a: 0, b: 0, c: 0, e: 0, abs: 0};
            if (!prev_retract[tool]) prev_retract[tool] = 0;

            activeToolOffset = toolOffsets[tool];
            if (!activeToolOffset) activeToolOffset = {x: 0, y: 0};
        }

        // If move is on a new height and it's not extruding and
        // it's not currently already in a Z-lift, assume it's possibly a Z-lift
        if (typeof(z) !== 'undefined' && z !== prevZ && !extrude && !zLift) {
            zLift = true;
            zLiftZ = prevZ;
        }
        // We're extruding, Z-lift is over
        if (extrude) {
            zLift = false;
        }

        if (typeof(z) !== 'undefined' && z !== prevZ) {
            if (z_heights[z] !== undefined) {
                layer = z_heights[z];
            } else {
                layer = model.length;
                z_heights[z] = layer;
            }

            sendLayer = layer;
            sendLayerZ = z;
            prevZ = z;
        } else if (typeof(z) === 'undefined' && typeof(prevZ) !== 'undefined') {
            if (z_heights.hasOwnProperty(prevZ)) {
                layer = z_heights[prevZ];
            } else {
                layer = model.length;
                z_heights[prevZ] = layer;
            }
        }

        if (addToModel) {
            if (!model[layer]) model[layer] = [];
            var command = {
                x: x,
                y: y,
                z: z,
                i: center_i,
                j: center_j,
                direction: direction,
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
            };

            if (zLift) {
                // Insert zLift moves for later processing
                zLiftMoves.push({
                    command: command,
                    layer: layer
                });
            } else if (zLiftMoves.length > 0) {
                // there's something to be checked in the Z-lift cache
                if (prevZ === zLiftZ) {
                    zLiftMoves.forEach(function (zLiftMove) {
                        model[zLiftMove.layer].splice(model[layer].indexOf(zLiftMove.command), 1);
                        model[z_heights[zLiftZ]].push(zLiftMove.command);
                    });
                }
                // clear up cached Z-lift moves
                zLiftMoves = [];
                zLiftZ = undefined;
            }


            model[layer].push(command);
        }

        if (move) {
            if (typeof(x) !== 'undefined') prevX = x;
            if (typeof(y) !== 'undefined') prevY = y;
        }

        if (typeof(sendLayer) !== "undefined") {
            if (i - lastSend > gcode.length * 0.02 && sendMultiLayer.length !== 0) {
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
    sendMultiLayerToParent(sendMultiLayer, sendMultiLayerZ, i / gcode.length * 100);
};


var parseGCode = function (message) {
    gcode = message.gcode;
    firstReport = message.options.firstReport;
    toolOffsets = message.options.toolOffsets;
    if (!toolOffsets || toolOffsets.length === 0) toolOffsets = [{x: 0, y: 0}];
    bed = message.options.bed;
    ignoreOutsideBed = message.options.ignoreOutsideBed;
    g90InfluencesExtruder = message.options.g90InfluencesExtruder;

    doParse();
    gcode = [];
    self.postMessage({
        "cmd": "returnModel",
        "msg": {}
    });
};

var runAnalyze = function (message) {
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
    boundingBox = {minX: undefined, maxX: undefined, minY: undefined, maxY: undefined, minZ: undefined, maxZ: undefined};
    filamentByLayer = {};
    totalFilament = 0;
    printTime = 0;
    printTimeByLayer = {};
    layerHeight = 0;
    layerCnt = 0;
    speeds = {extrude: [], retract: [], move: []};
    speedsByLayer = {extrude: {}, retract: {}, move: {}};
};

var setOption = function (options) {
    for (var opt in options) {
        if (!options.hasOwnProperty(opt)) continue;
        gCodeOptions[opt] = options[opt];
    }
};

onmessage = function (e) {
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
