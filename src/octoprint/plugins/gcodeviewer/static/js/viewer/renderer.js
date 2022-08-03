/**
 * User: hudbrog (hudbrog@gmail.com)
 * Date: 10/20/12
 * Time: 1:36 PM
 * To change this template use File | Settings | File Templates.
 */

GCODE.renderer = (function () {
    // ***** PRIVATE ******
    var canvas;
    var ctx;

    var viewportChanged = true;
    var lineWidthFactor = 1 / 2.8;

    var zoomFactorDelta = 0.4;
    var gridStep = 10;
    var ctxHeight, ctxWidth;
    var prevX = 0,
        prevY = 0;
    var pixelRatio = window.devicePixelRatio || 1;

    var layerNumStore,
        progressStore = {from: 0, to: -1};
    var lastX, lastY;
    var dragStart;
    var scaleFactor = 1.1;
    var model = undefined;
    var modelInfo = undefined;
    var initialized = false;
    var renderOptions = {
        colorGrid: "#bbbbbb",
        bgColorGrid: "#ffffff",
        bgColorOffGrid: "#eeeeee",
        colorLine: ["#000000", "#3333cc", "#cc3333", "#33cc33", "#cc33cc"],
        colorMove: "#00ff00",
        colorRetract: "#ff0000",
        colorRestart: "#0000ff",
        colorHead: "#00ff00",
        colorSegmentStart: "#666666",

        showMoves: true,
        showRetracts: true,
        extrusionWidth: 1 * pixelRatio,
        // #000000", "#45c7ba",  "#a9533a", "#ff44cc", "#dd1177", "#eeee22", "#ffbb55", "#ff5511", "#777788"
        sizeRetractSpot: 2 * pixelRatio,
        sizeHeadSpot: 2 * pixelRatio,
        modelCenter: {x: 0, y: 0},
        differentiateColors: true,
        showNextLayer: false,
        showCurrentLayer: false,
        showPreviousLayer: false,
        showBoundingBox: false,
        showLayerBoundingBox: false,
        showFullSize: false,
        showHead: false,
        showSegmentStarts: false,
        sizeSegmentStart: 2 * pixelRatio,
        showDebugArcs: false,
        chromeArcFix: false,

        moveModel: true,
        zoomInOnModel: false,
        zoomInOnBed: false,
        centerViewport: false,
        invertAxes: {x: false, y: false},

        bed: {x: 200, y: 200},
        container: undefined,

        onInternalOptionChange: undefined,

        onViewportChange: undefined,
        onDragStart: undefined, // Cancellable (return false)
        onDrag: undefined, // Cancellable (return false)
        onDragStop: undefined
    };

    // offset due to dragging
    var offsetModelX = 0,
        offsetModelY = 0;

    // TODO: remove in 1.7.0
    var offsetBedX = 0,
        offsetBedY = 0;

    // scale due to zooming
    var scaleX = 1,
        scaleY = 1;

    var speeds = [];
    var speedsByLayer = {};
    var currentInvertX = false,
        currentInvertY = false;

    var deg0 = 0.0;
    var deg90 = Math.PI / 2.0;
    var deg180 = Math.PI;
    var deg270 = Math.PI * 1.5;
    var deg360 = Math.PI * 2.0;

    var layerCache = [];

    var decompress = function (data) {
        if (!(data instanceof Uint8Array)) return data;

        return JSON.parse(pako.inflate(data, {to: "string"}));
    };

    var getLayer = function (layer) {
        if (!model[layer]) return undefined;
        if (!layerCache[layer]) layerCache[layer] = decompress(model[layer]);

        return layerCache[layer];
    };

    var cleanCache = function (layer) {
        var newCache = [];
        for (var l in layerCache) {
            if (l == layer || l == layer + 1) newCache[l] = layerCache[l];
            if (l == layer - 1 && renderOptions["showPreviousLayer"])
                newCache[l] = layerCache[l];
        }

        layerCache = newCache;
    };

    function notifyIfViewportChanged() {
        if (viewportChanged) {
            if (renderOptions["onViewportChange"]) {
                renderOptions["onViewportChange"](ctx.getTransform());
            }
            viewportChanged = false;
        }
    }

    var reRender = function () {
        if (!model) return;

        log.debug(
            "Rerendering layer " +
                layerNumStore +
                " of " +
                model.length +
                " with " +
                GCODE.renderer.getLayerNumSegments(layerNumStore) +
                " segments"
        );

        applyOffsets(layerNumStore);
        applyZoom(layerNumStore);

        notifyIfViewportChanged();

        var p1 = ctx.transformedPoint(0, 0);
        var p2 = ctx.transformedPoint(canvas.width, canvas.height);
        ctx.clearRect(p1.x, p1.y, p2.x - p1.x, p2.y - p1.y);

        drawGrid();
        drawBoundingBox(layerNumStore);
        if (model && model.length) {
            if (layerNumStore < model.length) {
                if (renderOptions["showNextLayer"] && layerNumStore < model.length - 1) {
                    drawLayer(
                        layerNumStore + 1,
                        0,
                        GCODE.renderer.getLayerNumSegments(layerNumStore + 1),
                        true
                    );
                }
                if (renderOptions["showCurrentLayer"] && layerNumStore < model.length) {
                    drawLayer(
                        layerNumStore,
                        0,
                        GCODE.renderer.getLayerNumSegments(layerNumStore),
                        true
                    );
                }
                if (renderOptions["showPreviousLayer"] && layerNumStore > 0) {
                    drawLayer(
                        layerNumStore - 1,
                        0,
                        GCODE.renderer.getLayerNumSegments(layerNumStore - 1),
                        true
                    );
                }
                drawLayer(layerNumStore, progressStore.from, progressStore.to);
            } else {
                console.log("Got request to render non-existent layer");
            }

            cleanCache(layerNumStore);
        }
    };

    function getLayerBounds(layer) {
        if (!model || !model[layer]) return;

        var cmds = getLayer(layer);
        var firstExtrusion;
        var i;

        // find bounds based on x/y moves with extrusion only
        // if you want to change that criterion, this is the place to do it
        var factorIn = function (cmd) {
            return cmd && cmd.extrude && (cmd.x !== undefined || cmd.y !== undefined);
        };

        for (i = 0; i < cmds.length; i++) {
            if (factorIn(cmds[i])) break;
        }

        if (i === cmds.length) return;
        firstExtrusion = i;

        // initialize with guaranteed defined values and cut out a bunch of
        // testing for undefined cases
        var minX = cmds[firstExtrusion].prevX,
            maxX = cmds[firstExtrusion].prevX,
            minY = cmds[firstExtrusion].prevY,
            maxY = cmds[firstExtrusion].prevY;

        for (i = firstExtrusion; i < cmds.length; i++) {
            if (factorIn(cmds[i])) {
                minX = Math.min(minX, cmds[i].prevX);
                maxX = Math.max(maxX, cmds[i].prevX);
                if (cmds[i].x !== undefined) {
                    minX = Math.min(minX, cmds[i].x);
                    maxX = Math.max(maxX, cmds[i].x);
                }
                minY = Math.min(minY, cmds[i].prevY);
                maxY = Math.max(maxY, cmds[i].prevY);
                if (cmds[i].y !== undefined) {
                    minY = Math.min(minY, cmds[i].y);
                    maxY = Math.max(maxY, cmds[i].y);
                }
                if (!!cmds[i].direction) {
                    var dir = cmds[i].direction;
                    var arc = getArcParams(cmds[i]);

                    var startAngle, endAngle;
                    if (dir < 0) {
                        // cw: start = start and end = end
                        startAngle = arc.startAngle;
                        endAngle = arc.endAngle;
                    } else {
                        // ccw: start = end and end = start for clockwise
                        startAngle = arc.endAngle;
                        endAngle = arc.startAngle;
                    }

                    if (startAngle < 0) startAngle += deg360;
                    if (endAngle < 0) endAngle += deg360;

                    // from now on we only think in clockwise direction
                    var intersectsAngle = function (sA, eA, angle) {
                        return (
                            (sA >= angle && (eA <= angle || eA > sA)) ||
                            (sA <= angle && eA <= angle && eA > sA)
                        );
                    };

                    if (intersectsAngle(startAngle, endAngle, deg0)) {
                        // arc crosses positive x
                        maxX = Math.max(maxX, arc.x + arc.r);
                    }

                    if (intersectsAngle(startAngle, endAngle, deg90)) {
                        // arc crosses positive y
                        maxY = Math.max(maxY, arc.y + arc.r);
                    }

                    if (intersectsAngle(startAngle, endAngle, deg180)) {
                        // arc crosses negative x
                        minX = Math.min(minX, arc.x - arc.r);
                    }

                    if (intersectsAngle(startAngle, endAngle, deg270)) {
                        // arc crosses negative y
                        minY = Math.min(minY, arc.y - arc.r);
                    }
                }
            }
        }

        return {minX: minX, maxX: maxX, minY: minY, maxY: maxY};
    }

    function getArcParams(cmd) {
        var x = cmd.x !== undefined ? cmd.x : cmd.prevX;
        var y = cmd.y !== undefined ? cmd.y : cmd.prevY;

        var centerX = cmd.prevX + cmd.i;
        var centerY = cmd.prevY + cmd.j;
        return {
            x: centerX,
            y: centerY,
            r: Math.sqrt(cmd.i * cmd.i + cmd.j * cmd.j),
            startAngle: Math.atan2(cmd.prevY - centerY, cmd.prevX - centerX),
            endAngle: Math.atan2(y - centerY, x - centerX),
            startX: cmd.prevX,
            startY: cmd.prevY,
            endX: x,
            endY: y
        };
    }

    function trackTransforms(ctx) {
        var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        var xform = svg.createSVGMatrix();
        ctx.getTransform = function () {
            return xform;
        };

        var savedTransforms = [];
        var save = ctx.save;
        ctx.save = function () {
            savedTransforms.push(xform.translate(0, 0));
            return save.call(ctx);
        };
        var restore = ctx.restore;
        ctx.restore = function () {
            xform = savedTransforms.pop();
            viewportChanged = true;
            return restore.call(ctx);
        };

        var scale = ctx.scale;
        ctx.scale = function (sx, sy) {
            xform = xform.scaleNonUniform(sx, sy);
            viewportChanged = true;
            return scale.call(ctx, sx, sy);
        };
        var rotate = ctx.rotate;
        ctx.rotate = function (radians) {
            xform = xform.rotate((radians * 180) / Math.PI);
            viewportChanged = true;
            return rotate.call(ctx, radians);
        };
        var translate = ctx.translate;
        ctx.translate = function (dx, dy) {
            xform = xform.translate(dx, dy);
            viewportChanged = true;
            return translate.call(ctx, dx, dy);
        };
        var transform = ctx.transform;
        ctx.transform = function (a, b, c, d, e, f) {
            var m2 = svg.createSVGMatrix();
            m2.a = a;
            m2.b = b;
            m2.c = c;
            m2.d = d;
            m2.e = e;
            m2.f = f;
            xform = xform.multiply(m2);
            viewportChanged = true;
            return transform.call(ctx, a, b, c, d, e, f);
        };
        var setTransform = ctx.setTransform;
        ctx.setTransform = function (a, b, c, d, e, f) {
            xform.a = a;
            xform.b = b;
            xform.c = c;
            xform.d = d;
            xform.e = e;
            xform.f = f;
            viewportChanged = true;
            return setTransform.call(ctx, a, b, c, d, e, f);
        };
        var pt = svg.createSVGPoint();
        ctx.transformedPoint = function (x, y) {
            pt.x = x;
            pt.y = y;
            return pt.matrixTransform(xform.inverse());
        };
    }

    // replace arc for chrome, code from https://stackoverflow.com/a/11689752
    var bezierArc = function (x, y, radius, startAngle, endAngle, anticlockwise) {
        // Signed length of curve
        var signedLength;
        var tau = 2 * Math.PI;

        if (!anticlockwise && endAngle - startAngle >= tau) {
            signedLength = tau;
        } else if (anticlockwise && startAngle - endAngle >= tau) {
            signedLength = -tau;
        } else {
            var delta = endAngle - startAngle;
            signedLength = delta - tau * Math.floor(delta / tau);

            // If very close to a full number of revolutions, make it full
            if (Math.abs(delta) > 1e-12 && signedLength < 1e-12) signedLength = tau;

            // Adjust if anti-clockwise
            if (anticlockwise && signedLength > 0) signedLength = signedLength - tau;
        }

        // Minimum number of curves; 1 per quadrant.
        var minCurves = Math.ceil(Math.abs(signedLength) / (Math.PI / 2));

        // Number of curves; square-root of radius (or minimum)
        var numCurves = Math.ceil(Math.max(minCurves, Math.sqrt(radius)));

        // "Radius" of control points to ensure that the middle point
        // of the curve is exactly on the circle radius.
        var cpRadius = radius * (2 - Math.cos(signedLength / (numCurves * 2)));

        // Angle step per curve
        var step = signedLength / numCurves;

        // Draw the circle
        this.lineTo(x + radius * Math.cos(startAngle), y + radius * Math.sin(startAngle));
        for (
            var i = 0, a = startAngle + step, a2 = startAngle + step / 2;
            i < numCurves;
            ++i, a += step, a2 += step
        )
            this.quadraticCurveTo(
                x + cpRadius * Math.cos(a2),
                y + cpRadius * Math.sin(a2),
                x + radius * Math.cos(a),
                y + radius * Math.sin(a)
            );
    };

    var applyContextPatches = function () {
        if (!ctx.origArc) ctx.origArc = ctx.arc;
        ctx.circle = function (x, y, r) {
            ctx.origArc(x, y, r, 0, 2 * Math.PI, true);
        };

        if (navigator.userAgent.toLowerCase().indexOf("chrome") > -1) {
            if (renderOptions["chromeArcFix"]) {
                ctx.arc = bezierArc;
                log.info("Chrome Arc Fix enabled");
            } else {
                ctx.arc = ctx.origArc;
                log.info("Chrome Arc Fix disabled");
            }
        }
    };

    var startCanvas = function () {
        var jqueryCanvas = $(renderOptions["container"]);
        //jqueryCanvas.css("background-color", renderOptions["bgColorOffGrid"]);
        canvas = jqueryCanvas[0];

        ctx = canvas.getContext("2d");
        applyContextPatches();

        canvas.style.height = canvas.height + "px";
        canvas.style.width = canvas.width + "px";
        canvas.height = canvas.height * pixelRatio;
        canvas.width = canvas.width * pixelRatio;
        ctxHeight = canvas.height;
        ctxWidth = canvas.width;
        lastX = ctxWidth / 2;
        lastY = ctxHeight / 2;
        ctx.lineWidth = 2 * lineWidthFactor;
        ctx.lineCap = "round";
        trackTransforms(ctx);

        // dragging => translating
        canvas.addEventListener(
            "mousedown",
            function (event) {
                document.body.style.mozUserSelect =
                    document.body.style.webkitUserSelect =
                    document.body.style.userSelect =
                        "none";

                // remember starting point of dragging gesture
                lastX = (event.offsetX || event.pageX - canvas.offsetLeft) * pixelRatio;
                lastY = (event.offsetY || event.pageY - canvas.offsetTop) * pixelRatio;

                var pt = ctx.transformedPoint(lastX, lastY);
                if (
                    !renderOptions["onDragStart"] ||
                    renderOptions["onDragStart"](pt) !== false
                )
                    dragStart = pt;
            },
            false
        );

        canvas.addEventListener(
            "mousemove",
            function (event) {
                // save current mouse coordinates
                lastX = (event.offsetX || event.pageX - canvas.offsetLeft) * pixelRatio;
                lastY = (event.offsetY || event.pageY - canvas.offsetTop) * pixelRatio;

                // mouse movement => dragged
                if (dragStart !== undefined) {
                    // translate
                    var pt = ctx.transformedPoint(lastX, lastY);

                    if (renderOptions["onDrag"] && renderOptions["onDrag"](pt) === false)
                        return;

                    ctx.translate(pt.x - dragStart.x, pt.y - dragStart.y);
                    reRender();

                    renderOptions["centerViewport"] = false;
                    renderOptions["zoomInOnModel"] = false;
                    renderOptions["zoomInOnBed"] = false;
                    offsetModelX = 0;
                    offsetModelY = 0;
                    offsetBedX = 0;
                    offsetBedY = 0;
                    scaleX = 1;
                    scaleY = 1;

                    if (renderOptions["onInternalOptionChange"] !== undefined) {
                        renderOptions["onInternalOptionChange"]({
                            centerViewport: false,
                            moveModel: false,
                            zoomInOnModel: false,
                            zoomInOnBed: false
                        });
                    }
                }
            },
            false
        );

        canvas.addEventListener(
            "mouseup",
            function (event) {
                // reset dragStart
                dragStart = undefined;

                if (renderOptions["onDragStop"]) {
                    var x =
                        (event.offsetX || event.pageX - canvas.offsetLeft) * pixelRatio;
                    var y =
                        (event.offsetY || event.pageY - canvas.offsetTop) * pixelRatio;
                    renderOptions["onDragStop"](ctx.transformedPoint(x, y));
                }
            },
            false
        );

        // mouse wheel => zooming
        var zoom = function (clicks) {
            // focus on last mouse position prior to zoom
            var pt = ctx.transformedPoint(lastX, lastY);
            ctx.translate(pt.x, pt.y);

            // determine zooming factor and perform zoom
            var factor = Math.pow(scaleFactor, clicks);
            ctx.scale(factor, factor);

            // return to old position
            ctx.translate(-pt.x, -pt.y);

            // render
            reRender();

            // disable conflicting options
            renderOptions["zoomInOnModel"] = false;
            renderOptions["zoomInOnBed"] = false;
            offsetModelX = 0;
            offsetModelY = 0;
            offsetBedX = 0;
            offsetBedY = 0;
            scaleX = 1;
            scaleY = 1;

            if (renderOptions["onInternalOptionChange"] !== undefined) {
                renderOptions["onInternalOptionChange"]({
                    zoomInOnModel: false,
                    zoomInOnBed: false
                });
            }
        };
        var handleScroll = function (event) {
            var delta;

            // determine zoom direction & delta
            if (event.detail < 0 || event.wheelDelta > 0) {
                delta = zoomFactorDelta;
            } else {
                delta = -1 * zoomFactorDelta;
            }
            if (delta) zoom(delta);

            return event.preventDefault() && false;
        };
        canvas.addEventListener("DOMMouseScroll", handleScroll, false);
        canvas.addEventListener("mousewheel", handleScroll, false);
    };

    var drawGrid = function () {
        ctx.translate(offsetBedX, offsetBedY);
        if (renderOptions["bed"]["circular"]) {
            drawCircularGrid();
        } else {
            drawRectangularGrid();
        }
        ctx.translate(-offsetBedX, -offsetBedY);
    };

    var drawRectangularGrid = function () {
        var x, y;
        var width = renderOptions["bed"]["x"];
        var height = renderOptions["bed"]["y"];

        var minX, maxX, minY, maxY;
        if (renderOptions["bed"]["centeredOrigin"]) {
            var halfWidth = width / 2;
            var halfHeight = height / 2;

            minX = -halfWidth;
            maxX = halfWidth;
            minY = -halfHeight;
            maxY = halfHeight;
        } else {
            minX = 0;
            maxX = width;
            minY = 0;
            maxY = height;
        }

        //~ bed outline and origin
        ctx.beginPath();
        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.fillStyle = "#ffffff";
        ctx.lineWidth = 2 * lineWidthFactor;

        // outline
        ctx.rect(minX, minY, width, height);

        // origin
        ctx.moveTo(minX, 0);
        ctx.lineTo(maxX, 0);
        ctx.moveTo(0, minY);
        ctx.lineTo(0, maxY);

        // draw
        ctx.fill();
        ctx.stroke();

        // draw origin
        ctx.beginPath();
        ctx.circle(0, 0, 2);
        ctx.stroke();

        //~~ grid starting from origin
        ctx.strokeStyle = renderOptions["colorGrid"];
        var gridline = 0;
        for (x = 0; x <= maxX; x += gridStep) {
            ctx.beginPath();
            if (gridline % 5 === 0) {
                // every fifth line, including the center
                ctx.lineWidth = 1.5 * lineWidthFactor;
            } else {
                ctx.lineWidth = lineWidthFactor;
            }
            gridline += 1;

            ctx.moveTo(x, minY);
            ctx.lineTo(x, maxY);

            if (renderOptions["bed"]["centeredOrigin"]) {
                ctx.moveTo(-1 * x, minY);
                ctx.lineTo(-1 * x, maxY);
            }
            ctx.stroke();
        }

        gridline = 0;
        for (y = 0; y <= maxY; y += gridStep) {
            ctx.beginPath();
            if (gridline % 5 === 0) {
                // every fifth line, including the center
                ctx.lineWidth = 1.5 * lineWidthFactor;
            } else {
                ctx.lineWidth = lineWidthFactor;
            }
            gridline += 1;

            ctx.moveTo(minX, y);
            ctx.lineTo(maxX, y);

            if (renderOptions["bed"]["centeredOrigin"]) {
                ctx.moveTo(minX, -1 * y);
                ctx.lineTo(maxX, -1 * y);
            }
            ctx.stroke();
        }
    };

    var drawCircularGrid = function () {
        var i;

        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.fillStyle = "#ffffff";
        ctx.lineWidth = 2 * lineWidthFactor;

        //~~ bed outline & origin
        ctx.beginPath();

        // outline
        var r = renderOptions["bed"]["r"];
        ctx.circle(0, 0, r);

        // origin
        ctx.moveTo(-1 * r, 0);
        ctx.lineTo(r, 0);
        ctx.moveTo(0, r);
        ctx.lineTo(0, -1 * r);

        // draw
        ctx.fill();
        ctx.stroke();

        // draw origin
        ctx.beginPath();
        ctx.circle(0, 0, 2);
        ctx.stroke();

        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.lineWidth = lineWidthFactor;

        //~~ grid starting from origin
        ctx.beginPath();
        for (i = 0; i <= r; i += gridStep) {
            var x = i;
            var y = Math.sqrt(r * r - x * x);

            ctx.moveTo(x, -1 * y);
            ctx.lineTo(x, y);

            ctx.moveTo(y, -1 * x);
            ctx.lineTo(-1 * y, -1 * x);

            ctx.moveTo(-1 * x, -1 * y);
            ctx.lineTo(-1 * x, y);

            ctx.moveTo(y, x);
            ctx.lineTo(-1 * y, x);
        }
        ctx.stroke();
    };

    var drawBoundingBox = function (layerNum) {
        if (!modelInfo) return;

        var minX, minY, width, height;

        var draw = function (x, y, w, h, c) {
            ctx.beginPath();
            ctx.strokeStyle = c;
            ctx.setLineDash([2, 5]);

            ctx.rect(x, y, w, h);

            ctx.stroke();
        };

        if (renderOptions["showFullSize"]) {
            minX = modelInfo.min.x;
            minY = modelInfo.min.y;
            width = modelInfo.modelSize.x;
            height = modelInfo.modelSize.y;
            draw(minX, minY, width, height, "#0000ff");
        }

        if (renderOptions["showBoundingBox"]) {
            minX = modelInfo.boundingBox.minX;
            minY = modelInfo.boundingBox.minY;
            width = modelInfo.boundingBox.maxX - minX;
            height = modelInfo.boundingBox.maxY - minY;
            draw(minX, minY, width, height, "#ff0000");
        }

        if (renderOptions["showLayerBoundingBox"]) {
            var layerBounds = getLayerBounds(layerNum);
            if (layerBounds) {
                minX = layerBounds.minX;
                minY = layerBounds.minY;
                width = layerBounds.maxX - minX;
                height = layerBounds.maxY - minY;
                draw(minX, minY, width, height, "#00ff00");
            }
        }

        ctx.setLineDash([1, 0]);
    };

    var drawTriangle = function (centerX, centerY, length, up) {
        /*
         *             (cx,cy)
         *                *             ^
         *               / \            |
         *              /   \           |
         *             /     \          |
         *            / (x,y) \         | h
         *           /         \        |
         *          /           \       |
         *         /             \      |
         *        *---------------*     v
         *    (ax,ay)           (bx,by)
         */

        var ax, bx, cx, ay, by, cy;
        var h = Math.sqrt(0.75 * length * length) / 2;

        ax = centerX - length / 2;
        bx = ax + length;
        cx = centerX;

        if (up) {
            ay = centerY - h;
            by = centerY - h;
            cy = centerY + h;
        } else {
            ay = centerY + h;
            by = centerY + h;
            cy = centerY - h;
        }

        var origLineJoin = ctx.lineJoin;
        ctx.lineJoin = "miter";

        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(bx, by);
        ctx.moveTo(bx, by);
        ctx.lineTo(cx, cy);
        ctx.lineTo(ax, ay);
        ctx.stroke();
        ctx.fill();

        ctx.lineJoin = origLineJoin;
    };

    var drawCross = function (centerX, centerY, size) {
        var x1, y1, x2, y2;

        var half = size / 2;
        x1 = centerX - half;
        x2 = centerX + half;
        y1 = centerY - half;
        y2 = centerY + half;

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.moveTo(x1, y2);
        ctx.lineTo(x2, y1);
        ctx.stroke();
    };

    var drawDebugArc = function (arc, ccw) {
        ctx.moveTo(arc.x, arc.y);
        ctx.lineTo(arc.startX, arc.startY);
        ctx.moveTo(arc.x, arc.y);
        ctx.lineTo(arc.endX, arc.endY);
        ctx.moveTo(arc.startX, arc.startY);
        ctx.lineTo(arc.endX, arc.endY);
        ctx.moveTo(arc.startX, arc.startY);
        ctx.arc(arc.x, arc.y, arc.r, arc.startAngle, arc.endAngle, ccw);
    };

    var drawLayer = function (layerNum, fromProgress, toProgress, isNotCurrentLayer) {
        log.trace(
            "Drawing layer " +
                layerNum +
                " from " +
                fromProgress +
                " to " +
                toProgress +
                " (current: " +
                !isNotCurrentLayer +
                ")"
        );

        var i;

        //~~ store current layer values

        isNotCurrentLayer = isNotCurrentLayer !== undefined ? isNotCurrentLayer : false;

        if (!model || !model[layerNum]) return;

        var cmds = getLayer(layerNum);
        var x, y;

        //~~ find our initial prevX/prevY tuple

        if (cmds[0].prevX !== undefined && cmds[0].prevY !== undefined) {
            // command contains prevX/prevY values, use those
            prevX = cmds[0].prevX;
            prevY = cmds[0].prevY;
        } else if (fromProgress > 0) {
            // previous command in same layer exists, use x/y as prevX/prevY
            prevX = cmds[fromProgress - 1].x;
            prevY = cmds[fromProgress - 1].y;
        } else if (model[layerNum - 1]) {
            // previous layer exists, use last x/y as prevX/prevY
            prevX = undefined;
            prevY = undefined;
            var prevModelLayer = getLayer(layerNum - 1);
            for (i = prevModelLayer.length - 1; i >= 0; i--) {
                if (prevX === undefined && prevModelLayer[i].x !== undefined) {
                    prevX = prevModelLayer[i].x;
                    if (prevY !== undefined) break;
                }
                if (prevY === undefined && prevModelLayer[i].y !== undefined) {
                    prevY = prevModelLayer[i].y;
                    if (prevX !== undefined) break;
                }
            }
        }

        // if we did not find prevX or prevY, set it to 0 (might be that we are on the first command of the first layer,
        // or it's just a very weird model...)
        if (prevX === undefined) prevX = 0;
        if (prevY === undefined) prevY = 0;

        //~~ render this layer's commands

        var sizeRetractSpot = renderOptions["sizeRetractSpot"] * lineWidthFactor * 2;
        var sizeSegmentStart = renderOptions["sizeSegmentStart"] * lineWidthFactor * 2;

        // alpha value (100% if current layer is being rendered, 30% otherwise)
        // Note - If showing currently layer as preview - also render it at 30% and draw the progress over the top at 100%
        var alpha =
            (renderOptions["showNextLayer"] ||
                renderOptions["showCurrentLayer"] ||
                renderOptions["showPreviousLayer"]) &&
            isNotCurrentLayer
                ? 0.3
                : 1.0;

        var colorLine = {};
        var colorMove = {};
        var colorRetract = {};
        var colorRestart = {};
        var colorSegmentStart = {};

        function getColorLineForTool(tool) {
            var rv = colorLine[tool];
            if (rv === undefined) {
                var lineColor = renderOptions["colorLine"][tool];
                if (lineColor === undefined) lineColor = renderOptions["colorLine"][0];
                var shade = tool * 0.15;
                rv = colorLine[tool] = pusher
                    .color(lineColor)
                    .shade(shade)
                    .alpha(alpha)
                    .html();
            }
            return rv;
        }

        function getColorMoveForTool(tool) {
            var rv = colorMove[tool];
            if (rv === undefined) {
                var shade = tool * 0.15;
                rv = colorMove[tool] = pusher
                    .color(renderOptions["colorMove"])
                    .shade(shade)
                    .alpha(alpha)
                    .html();
            }
            return rv;
        }

        function getColorRetractForTool(tool) {
            var rv = colorRetract[tool];
            if (rv === undefined) {
                var shade = tool * 0.15;
                rv = colorRetract[tool] = pusher
                    .color(renderOptions["colorRetract"])
                    .shade(shade)
                    .alpha(alpha)
                    .html();
            }
            return rv;
        }

        function getColorRestartForTool(tool) {
            var rv = colorRestart[tool];
            if (rv === undefined) {
                var shade = tool * 0.15;
                rv = colorRestart[tool] = pusher
                    .color(renderOptions["colorRestart"])
                    .shade(shade)
                    .alpha(alpha)
                    .html();
            }
            return rv;
        }

        function getColorSegmentStartForTool(tool) {
            var rv = colorSegmentStart[tool];
            if (rv === undefined) {
                var shade = tool * 0.15;
                rv = colorSegmentStart[tool] = pusher
                    .color(renderOptions["colorSegmentStart"])
                    .shade(shade)
                    .alpha(alpha)
                    .html();
            }
            return rv;
        }

        var prevPathType = "fill";
        function strokePathIfNeeded(newPathType, strokeStyle) {
            if (newPathType !== prevPathType || newPathType === "fill") {
                if (prevPathType !== "fill") {
                    ctx.stroke();
                }
                prevPathType = newPathType;

                ctx.beginPath();
                if (newPathType !== "fill") {
                    ctx.strokeStyle = strokeStyle;
                    ctx.moveTo(prevX, prevY);
                }
            }
        }

        ctx.lineJoin = "round";

        for (i = fromProgress; i <= toProgress; i++) {
            if (typeof cmds[i] === "undefined") continue;
            var cmd = cmds[i];

            if (cmd.prevX !== undefined && cmd.prevY !== undefined) {
                // override new (prevX, prevY)
                prevX = cmd.prevX;
                prevY = cmd.prevY;
            }

            // new x
            if (cmd.x === undefined || isNaN(cmd.x)) {
                x = prevX;
            } else {
                x = cmd.x;
            }

            // new y
            if (cmd.y === undefined || isNaN(cmd.y)) {
                y = prevY;
            } else {
                y = cmd.y;
            }

            // current tool
            var tool = cmd.tool || 0;

            if (!cmd.extrude && !cmd.noMove) {
                // neither extrusion nor move
                if (cmd.retract == -1) {
                    // retract => draw dot if configured to do so
                    if (renderOptions["showRetracts"] && !isNotCurrentLayer) {
                        strokePathIfNeeded("fill");
                        ctx.fillStyle = getColorRetractForTool(tool);
                        ctx.strokeStyle = ctx.fillStyle;
                        drawTriangle(prevX, prevY, sizeRetractSpot, true);
                    }
                }

                strokePathIfNeeded("move", getColorMoveForTool(tool));
                if (renderOptions["showMoves"] && !isNotCurrentLayer) {
                    // move => draw line from (prevX, prevY) to (x, y) in move color
                    ctx.lineWidth = lineWidthFactor;

                    if (cmd.direction !== undefined && cmd.direction !== 0) {
                        var arc = getArcParams(cmd);
                        var ccw = cmd.direction < 0; // Y-axis is inverted so direction is also inverted
                        ctx.arc(arc.x, arc.y, arc.r, arc.startAngle, arc.endAngle, ccw);
                    } else {
                        ctx.lineTo(x, y);
                    }
                }
            } else if (cmd.extrude) {
                if (cmd.retract == 0) {
                    // no retraction => real extrusion move, use tool color to draw line
                    strokePathIfNeeded("extrude", getColorLineForTool(tool));
                    ctx.lineWidth = renderOptions["extrusionWidth"] * lineWidthFactor;
                    if (cmd.direction !== undefined && cmd.direction !== 0) {
                        var arc = getArcParams(cmd);
                        var ccw = cmd.direction < 0; // Y-axis is inverted so direction is also inverted

                        if (renderOptions["showDebugArcs"] && !isNotCurrentLayer) {
                            strokePathIfNeeded("debugarc", "#ff0000");
                            drawDebugArc(arc, ccw);
                            strokePathIfNeeded("extrude", getColorLineForTool(tool));
                        }

                        ctx.arc(arc.x, arc.y, arc.r, arc.startAngle, arc.endAngle, ccw);
                    } else {
                        ctx.lineTo(x, y);
                    }
                } else {
                    // we were previously retracting, now we are restarting => draw dot if configured to do so
                    if (renderOptions["showRetracts"] && !isNotCurrentLayer) {
                        strokePathIfNeeded("fill");
                        ctx.fillStyle = getColorRestartForTool(tool);
                        ctx.strokeStyle = ctx.fillStyle;
                        drawTriangle(prevX, prevY, sizeRetractSpot, false);
                    }
                }

                if (renderOptions["showSegmentStarts"] && !isNotCurrentLayer) {
                    strokePathIfNeeded("fill");
                    ctx.strokeStyle = getColorSegmentStartForTool(tool);
                    drawCross(x, y, sizeSegmentStart);
                }
            }

            // set new (prevX, prevY)
            prevX = x;
            prevY = y;
        }

        if (prevPathType != "fill") {
            ctx.stroke();
        }

        if (renderOptions["showHead"] && !isNotCurrentLayer) {
            var sizeHeadSpot =
                renderOptions["sizeHeadSpot"] * lineWidthFactor + lineWidthFactor / 2;
            var shade = tool * 0.15;
            ctx.fillStyle = pusher
                .color(renderOptions["colorHead"])
                .shade(shade)
                .alpha(alpha)
                .html();
            ctx.beginPath();
            ctx.circle(prevX, prevY, sizeHeadSpot);
            ctx.fill();
        }
    };

    var applyOffsets = function (layerNum) {
        var canvasCenter;
        var layerBounds;

        // determine bed and model offsets
        if (ctx) ctx.translate(-offsetModelX, -offsetModelY);
        if (renderOptions["centerViewport"] || renderOptions["zoomInOnModel"]) {
            canvasCenter = ctx.transformedPoint(canvas.width / 2, canvas.height / 2);
            layerBounds = getLayerBounds(layerNum);
            if (layerBounds) {
                offsetModelX = canvasCenter.x - (layerBounds.minX + layerBounds.maxX) / 2;
                offsetModelY = canvasCenter.y - (layerBounds.minY + layerBounds.maxY) / 2;
            } else {
                offsetModelX = 0;
                offsetModelY = 0;
            }
            offsetBedX = 0;
            offsetBedY = 0;
        } else if (renderOptions["moveModel"]) {
            layerBounds = getLayerBounds(layerNum);
            if (layerBounds) {
                offsetModelX =
                    renderOptions["bed"]["x"] / 2 -
                    (layerBounds.minX + layerBounds.maxX) / 2;
                offsetModelY =
                    renderOptions["bed"]["y"] / 2 -
                    (layerBounds.minY + layerBounds.maxY) / 2;
                offsetBedX =
                    -1 *
                    (renderOptions["bed"]["x"] / 2 -
                        (layerBounds.minX + layerBounds.maxX) / 2);
                offsetBedY =
                    -1 *
                    (renderOptions["bed"]["y"] / 2 -
                        (layerBounds.minY + layerBounds.maxY) / 2);
            }
        } else {
            offsetModelX = 0;
            offsetModelY = 0;
            offsetBedX = 0;
            offsetBedY = 0;
        }
        if (ctx) ctx.translate(offsetModelX, offsetModelY);
    };

    var applyZoom = function (layerNum) {
        // get middle of canvas
        var pt = ctx.transformedPoint(canvas.width / 2, canvas.height / 2);

        // get current transform
        var transform = ctx.getTransform();

        // move to middle of canvas, reset scale, move back
        if (scaleX && scaleY && transform.a && transform.d) {
            ctx.translate(pt.x, pt.y);
            ctx.scale(1 / scaleX, 1 / scaleY);
            ctx.translate(-pt.x, -pt.y);
            transform = ctx.getTransform();
        }

        if (renderOptions["zoomInOnModel"]) {
            var layerBounds = getLayerBounds(layerNum);
            if (layerBounds) {
                // if we need to zoom in on model, scale factor is calculated by longer side of object in relation to that axis of canvas
                // limited arbitrarily to 50 x extrusion width, to prevent extreme disorienting zoom
                var width = Math.max(
                    layerBounds.maxX - layerBounds.minX,
                    renderOptions["extrusionWidth"] * 50
                );
                var length = Math.max(
                    layerBounds.maxY - layerBounds.minY,
                    renderOptions["extrusionWidth"] * 50
                );

                var scaleF =
                    width > length
                        ? (canvas.width - 10) / width
                        : (canvas.height - 10) / length;
                if (transform.a && transform.d) {
                    scaleX =
                        (scaleF / transform.a) *
                        (renderOptions["invertAxes"]["x"] ? -1 : 1);
                    scaleY =
                        (scaleF / transform.d) *
                        (renderOptions["invertAxes"]["y"] ? 1 : -1);
                    ctx.translate(pt.x, pt.y);
                    ctx.scale(scaleX, scaleY);
                    ctx.translate(-pt.x, -pt.y);
                }
            }
        }
    };

    var applyInversion = function () {
        var width = canvas.width - 10;
        var height = canvas.height - 10;

        // de-invert
        if (currentInvertX || currentInvertY) {
            ctx.scale(currentInvertX ? -1 : 1, currentInvertY ? -1 : 1);
            ctx.translate(currentInvertX ? -width : 0, currentInvertY ? height : 0);
        }

        // get settings
        var invertX = renderOptions["invertAxes"]["x"];
        var invertY = renderOptions["invertAxes"]["y"];

        // invert
        if (invertX || invertY) {
            ctx.translate(invertX ? width : 0, invertY ? -height : 0);
            ctx.scale(invertX ? -1 : 1, invertY ? -1 : 1);
        }

        // save for later
        currentInvertX = invertX;
        currentInvertY = invertY;
    };

    var resetViewport = function () {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.scale(1, -1); // invert y axis

        var bedWidth = renderOptions["bed"]["x"];
        var bedHeight = renderOptions["bed"]["y"];
        if (renderOptions["bed"]["circular"]) {
            bedWidth = bedHeight = renderOptions["bed"]["r"] * 2;
        }

        // Ratio of bed to canvas viewport
        var viewportRatio = Math.min(
            (canvas.width - 10) / bedWidth,
            (canvas.height - 10) / bedHeight
        );

        // Apply initial translation to center the bed in the viewport
        var translationX, translationY;
        if (renderOptions["bed"]["circular"] || renderOptions["bed"]["centeredOrigin"]) {
            translationX = canvas.width / 2;
            translationY = canvas.height / 2;
        } else {
            translationX = (canvas.width - bedWidth * viewportRatio) / 2;
            translationY =
                bedHeight * viewportRatio +
                (canvas.height - bedHeight * viewportRatio) / 2;
        }

        ctx.translate(translationX, -translationY);
        ctx.scale(viewportRatio, viewportRatio);

        // Scaling to apply to move lines and extrusion/retraction markers
        lineWidthFactor = 1 / viewportRatio;

        offsetModelX = 0;
        offsetModelY = 0;
        offsetBedX = 0;
        offsetBedY = 0;
    };

    // ***** PUBLIC *******
    return {
        init: function () {
            startCanvas();
            resetViewport();
            initialized = true;
        },
        setOption: function (options) {
            var mustRefresh = false;
            var mustReset = false;
            var mustReapplyPatches = false;
            var dirty = false;
            for (var opt in options) {
                if (!renderOptions.hasOwnProperty(opt) || !options.hasOwnProperty(opt))
                    continue;
                if (options[opt] === undefined) continue;
                if (renderOptions[opt] == options[opt]) continue;

                dirty = true;
                renderOptions[opt] = options[opt];
                if (
                    $.inArray(opt, [
                        "moveModel",
                        "centerViewport",
                        "zoomInOnModel",
                        "bed",
                        "invertAxes",
                        "onViewportChange",
                        "chromeArcFix"
                    ]) > -1
                ) {
                    mustRefresh = true;
                }

                if ($.inArray(opt, ["bed", "onViewportChange"]) > -1) {
                    mustReset = true;
                }

                if ($.inArray(opt, ["chromeArcFix"]) > -1) {
                    mustReapplyPatches = true;
                }
            }

            if (!dirty) return;
            if (initialized) {
                if (mustReset) {
                    resetViewport();
                }
                if (mustReapplyPatches) {
                    applyContextPatches();
                }
                if (mustRefresh) {
                    this.refresh();
                } else {
                    reRender();
                }
            }
        },
        getOptions: function () {
            return renderOptions;
        },
        debugGetModel: function () {
            return model;
        },
        render: function (layerNum, fromProgress, toProgress) {
            if (!initialized) this.init();

            layerNumStore = layerNum;
            progressStore.from = fromProgress;
            progressStore.to = toProgress;

            reRender();
        },
        getModelNumLayers: function () {
            return model ? model.length : 1;
        },
        getLayerNumSegments: function (layer) {
            if (model) {
                return model[layer] ? getLayer(layer).length : 1;
            } else {
                return 1;
            }
        },
        getLayer: function (layer) {
            return getLayer(layer);
        },
        clear: function () {
            offsetModelX = 0;
            offsetModelY = 0;
            offsetBedX = 0;
            offsetBedY = 0;
            scaleX = 1;
            scaleY = 1;
            speeds = [];
            speedsByLayer = {};
            modelInfo = undefined;
            layerCache = [];

            this.doRender([], 0);
        },
        doRender: function (mdl, layerNum) {
            model = mdl;
            modelInfo = undefined;

            prevX = 0;
            prevY = 0;
            if (!initialized) this.init();

            var toProgress = 1;
            if (model && model.length) {
                modelInfo = GCODE.gCodeReader.getModelInfo();
                speeds = modelInfo.speeds;
                speedsByLayer = modelInfo.speedsByLayer;
                if (model[layerNum]) {
                    toProgress = getLayer(layerNum).length;
                }
            }

            applyInversion();
            scaleX = 1;
            scaleY = 1;

            this.render(layerNum, 0, toProgress);
        },
        refresh: function (layerNum) {
            if (layerNum === undefined) layerNum = layerNumStore;
            this.doRender(model, layerNum);
        },
        resetViewport: function () {
            resetViewport();
            reRender();
        },
        getZ: function (layerNum) {
            if (!model || !model[layerNum]) {
                return "-1";
            }
            var cmds = getLayer(layerNum);
            for (var i = 0; i < cmds.length; i++) {
                if (cmds[i].prevZ !== undefined) return cmds[i].prevZ;
            }
            return "-1";
        }
    };
})();
