/**
 * User: hudbrog (hudbrog@gmail.com)
 * Date: 10/21/12
 * Time: 7:31 AM
 */

GCODE.gCodeReader = (function () {
    // ***** PRIVATE ******
    var gcode, lines;
    var max = {x: undefined, y: undefined, z: undefined};
    var min = {x: undefined, y: undefined, z: undefined};
    var modelSize = {x: undefined, y: undefined, z: undefined};
    var boundingBox = {
        minX: undefined,
        maxX: undefined,
        minY: undefined,
        maxY: undefined,
        minZ: undefined,
        maxZ: undefined
    };
    var filamentByLayer = {};
    var printTimeByLayer;
    var totalFilament = 0;
    var printTime = 0;
    var speeds = {};
    var speedsByLayer = {};
    var gCodeOptions = {
        sortLayers: false,
        purgeEmptyLayers: true,
        analyzeModel: false,
        toolOffsets: [{x: 0, y: 0}],
        bed: {
            x: undefined,
            y: undefined,
            r: undefined,
            circular: undefined,
            centeredOrigin: undefined
        },
        ignoreOutsideBed: false,
        g90InfluencesExtruder: false,
        bedZ: 0,
        alwaysCompress: false,
        compressionSizeThreshold: 0,
        forceCompression: false
    };

    // This is the data as received from the worker.
    // This is preserved so the user can turn on or off
    // the "purgeEmptyLayers" option without forcing
    // a new download and reparsing of the gcode data
    // by the worker.
    var model = [];
    var emptyLayers = [];
    var percentageByLayer = [];

    // This is the data after being processed here in the
    // reader. It has empty indexes removed and
    // any layers without extrusion when the "purgeEmptyLayers"
    // option is set.
    // This is the data that is passed to the renderer.
    var rendererModel = undefined;
    var rendererEmptyLayers = undefined;
    var rendererPercentageByLayer = undefined;
    var layerPercentageLookup = [];

    var cachedLayer = undefined;
    var cachedCmd = undefined;

    var prepareGCode = function (totalSize) {
        if (!lines) return;
        gcode = [];
        var i, byteCount;

        byteCount = 0;
        for (i = 0; i < lines.length; i++) {
            byteCount += lines[i].length + 1; // line length + '\n'
            gcode.push({line: lines[i], percentage: (byteCount * 100) / totalSize});
        }
        lines = [];
    };

    var searchInPercentageTree = function (key) {
        function searchInLayers(lower, upper, key) {
            while (lower < upper) {
                var middle = Math.floor((lower + upper) / 2);

                if (
                    layerPercentageLookup[middle][0] <= key &&
                    layerPercentageLookup[middle][1] > key
                )
                    return middle;

                if (layerPercentageLookup[middle][0] > key) {
                    upper = middle - 1;
                } else {
                    lower = middle + 1;
                }
            }
            return lower;
        }

        function searchInCmds(layer, lower, upper, key) {
            var cmds = GCODE.renderer.getLayer(layer);
            while (lower < upper) {
                var middle = Math.floor((lower + upper) / 2);

                if (
                    cmds[middle].percentage == key ||
                    (cmds[middle].percentage <= key && cmds[middle + 1].percentage > key)
                )
                    return middle;

                if (cmds[middle].percentage > key) {
                    upper = middle - 1;
                } else {
                    lower = middle + 1;
                }
            }
            return lower;
        }

        if (rendererModel === undefined) return undefined;

        // this happens when the print is stopped.
        // just return last position to keep the last
        // position on screen.
        if (key == null) return {layer: cachedLayer, cmd: cachedCmd};

        var layer = searchInLayers(0, rendererModel.length - 1, key);
        var cmd = searchInCmds(layer, 0, GCODE.renderer.getLayer(layer).length - 1, key);

        // remember last position
        cachedLayer = layer;
        cachedCmd = cmd;

        return {layer: layer, cmd: cmd};
    };

    var cleanModel = function (m) {
        if (!m) return [];

        var result = [];
        rendererEmptyLayers = [];
        rendererPercentageByLayer = [];
        for (var i = 0; i < m.length; i++) {
            // remove any empty indexes that might be in the model.
            if (!m[i]) continue;
            // if the purgeEmptyLayers option is set, remove any layer
            // with commands but without extrusion.
            if (gCodeOptions["purgeEmptyLayers"] && emptyLayers[i]) continue;

            result.push(m[i]);
            rendererPercentageByLayer.push(percentageByLayer[i]);
            if (emptyLayers[i]) rendererEmptyLayers[result.length - 1] = true;
        }
        return result;
    };

    var rebuildLayerPercentageLookup = function (m) {
        var result = [];
        if (m && m.length > 0) {
            for (var i = 0; i < m.length - 1; i++) {
                // start is first command of current layer
                var start =
                    rendererPercentageByLayer[i] !== undefined
                        ? rendererPercentageByLayer[i]
                        : -1;

                var end = -1;
                for (var j = i + 1; j < m.length; j++) {
                    // end is percentage of first command that follows our start, might
                    // be later layers if the next layer is empty!
                    if (!rendererEmptyLayers[j]) {
                        end = rendererPercentageByLayer[j];
                        break;
                    }
                }
                result[i] = [start, end];
            }

            // final start-end-pair is start percentage of last layer and 100%
            result[result.length] = [rendererPercentageByLayer[m.length - 1], 100];
        }
        layerPercentageLookup = result;
    };

    // ***** PUBLIC *******
    return {
        clear: function () {
            model = [];
            max = {x: undefined, y: undefined, z: undefined};
            min = {x: undefined, y: undefined, z: undefined};
            modelSize = {x: undefined, y: undefined, z: undefined};
            boundingBox = {
                minX: undefined,
                maxX: undefined,
                minY: undefined,
                maxY: undefined,
                minZ: undefined,
                maxZ: undefined
            };
            rendererModel = undefined;
            rendererEmptyLayers = undefined;
            rendererPercentageByLayer = undefined;
            layerPercentageLookup = undefined;
            cachedLayer = undefined;
            cachedCmd = undefined;
        },

        loadFile: function (reader) {
            this.clear();

            var mustCompress =
                gCodeOptions["forceCompression"] ||
                gCodeOptions["alwaysCompress"] ||
                (gCodeOptions["compressionSizeThreshold"] > 0 &&
                    gCodeOptions["compressionSizeThreshold"] <= totalSize);

            GCODE.ui.worker.postMessage({
                cmd: "downloadAndParseGCode",
                msg: {
                    url: reader.url,
                    path: reader.path,
                    skipUntil: reader.skipUntil,
                    options: {
                        firstReport: 5,
                        toolOffsets: gCodeOptions["toolOffsets"],
                        bed: gCodeOptions["bed"],
                        ignoreOutsideBed: gCodeOptions["ignoreOutsideBed"],
                        g90InfluencesExtruder: gCodeOptions["g90InfluencesExtruder"],
                        bedZ: gCodeOptions["bedZ"],
                        compress: mustCompress
                    }
                }
            });
        },

        setOption: function (options) {
            var dirty = false;
            _.forOwn(options, function (value, key) {
                if (value === undefined) return;
                dirty = dirty || gCodeOptions[key] !== value;
                gCodeOptions[key] = value;
            });
            if (dirty) {
                if (model && model.length > 0) this.passDataToRenderer();
            }
        },

        passDataToRenderer: function () {
            rendererModel = cleanModel(model);
            rebuildLayerPercentageLookup(rendererModel);

            GCODE.renderer.doRender(rendererModel, 0);
            return rendererModel;
        },

        processLayersFromWorker: function (msg) {
            for (var i = 0; i < msg.layers.length; i++) {
                model[msg.layers[i]] = msg.model[msg.layers[i]];
            }
        },

        processAnalyzeModelDone: function (msg) {
            min = msg.min;
            max = msg.max;
            modelSize = msg.modelSize;
            boundingBox = msg.boundingBox;
            totalFilament = msg.totalFilament;
            filamentByLayer = msg.filamentByLayer;
            speeds = msg.speeds;
            speedsByLayer = msg.speedsByLayer;
            printTime = msg.printTime;
            printTimeByLayer = msg.printTimeByLayer;
            emptyLayers = msg.emptyLayers;
            percentageByLayer = msg.percentageByLayer;
        },

        getLayerFilament: function (z) {
            return filamentByLayer[z];
        },

        getLayerSpeeds: function (z) {
            return speedsByLayer[z] ? speedsByLayer[z] : {};
        },

        getModelInfo: function () {
            return {
                min: min,
                max: max,
                modelSize: modelSize,
                boundingBox: boundingBox,
                totalFilament: totalFilament,
                speeds: speeds,
                speedsByLayer: speedsByLayer,
                printTime: printTime,
                printTimeByLayer: printTimeByLayer
            };
        },

        getGCodeLines: function (layer, fromSegments, toSegments) {
            var result = {
                first: GCODE.renderer.getLayer(layer)[fromSegments].gcodeLine,
                last: GCODE.renderer.getLayer(layer)[toSegments].gcodeLine
            };
            return result;
        },

        getCmdIndexForPercentage: function (percentage) {
            return searchInPercentageTree(percentage);
        }
    };
})();
