/**
 * User: hudbrog (hudbrog@gmail.com)
 * Date: 10/20/12
 * Time: 1:36 PM
 * To change this template use File | Settings | File Templates.
 */


GCODE.renderer = (function(){
// ***** PRIVATE ******
    var canvas;
    var ctx;
    var zoomFactor= 2.8, zoomFactorDelta = 0.4;
    var gridSizeX=200,gridSizeY=200,gridStep=10;
    var ctxHeight, ctxWidth;
    var prevX=0, prevY=0;

    var sliderHor, sliderVer;
    var layerNumStore, progressStore={from: 0, to: -1};
    var lastX, lastY;
    var dragStart,dragged;
    var scaleFactor = 1.1;
    var model;
    var initialized=false;
    var renderOptions = {
        showMoves: true,
        showRetracts: true,
        colorGrid: "#bbbbbb",
        extrusionWidth: 1,
        // #000000", "#45c7ba",  "#a9533a", "#ff44cc", "#dd1177", "#eeee22", "#ffbb55", "#ff5511", "#777788"
        colorLine: ["#000000", "#3333cc", "#cc3333", "#33cc33", "#cc33cc"],
        colorMove: "#00ff00",
        colorRetract: "#ff0000",
        colorRestart: "#0000ff",
        sizeRetractSpot: 2,
        modelCenter: {x: 0, y: 0},
        moveModel: true,
        differentiateColors: true,
        showNextLayer: false
    };

    var offsetModelX=0, offsetModelY=0;
    var speeds = [];
    var speedsByLayer = {};


    var reRender = function(){
        var p1 = ctx.transformedPoint(0,0);
        var p2 = ctx.transformedPoint(canvas.width,canvas.height);
        ctx.clearRect(p1.x,p1.y,p2.x-p1.x,p2.y-p1.y);
        drawGrid();
        if(renderOptions['showNextLayer'] && layerNumStore < model.length - 1) {
            drawLayer(layerNumStore+1, 0, GCODE.renderer.getLayerNumSegments(layerNumStore+1), true);
        }
        drawLayer(layerNumStore, progressStore.from, progressStore.to);
    };

    function trackTransforms(ctx){
        var svg = document.createElementNS("http://www.w3.org/2000/svg",'svg');
        var xform = svg.createSVGMatrix();
        ctx.getTransform = function(){ return xform; };

        var savedTransforms = [];
        var save = ctx.save;
        ctx.save = function(){
            savedTransforms.push(xform.translate(0,0));
            return save.call(ctx);
        };
        var restore = ctx.restore;
        ctx.restore = function(){
            xform = savedTransforms.pop();
            return restore.call(ctx);
        };

        var scale = ctx.scale;
        ctx.scale = function(sx,sy){
            xform = xform.scaleNonUniform(sx,sy);
            return scale.call(ctx,sx,sy);
        };
        var rotate = ctx.rotate;
        ctx.rotate = function(radians){
            xform = xform.rotate(radians*180/Math.PI);
            return rotate.call(ctx,radians);
        };
        var translate = ctx.translate;
        ctx.translate = function(dx,dy){
            xform = xform.translate(dx,dy);
            return translate.call(ctx,dx,dy);
        };
        var transform = ctx.transform;
        ctx.transform = function(a,b,c,d,e,f){
            var m2 = svg.createSVGMatrix();
            m2.a=a; m2.b=b; m2.c=c; m2.d=d; m2.e=e; m2.f=f;
            xform = xform.multiply(m2);
            return transform.call(ctx,a,b,c,d,e,f);
        };
        var setTransform = ctx.setTransform;
        ctx.setTransform = function(a,b,c,d,e,f){
            xform.a = a;
            xform.b = b;
            xform.c = c;
            xform.d = d;
            xform.e = e;
            xform.f = f;
            return setTransform.call(ctx,a,b,c,d,e,f);
        };
        var pt  = svg.createSVGPoint();
        ctx.transformedPoint = function(x,y){
            pt.x=x; pt.y=y;
            return pt.matrixTransform(xform.inverse());
        }
    }


    var  startCanvas = function() {
        canvas = document.getElementById('canvas');

        // Проверяем понимает ли браузер canvas
        if (!canvas.getContext) {
            throw "exception";
        }

        ctx = canvas.getContext('2d'); // Получаем 2D контекст
        ctxHeight = canvas.height;
        ctxWidth = canvas.width;
        lastX = ctxWidth/2;
        lastY = ctxHeight/2;
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        trackTransforms(ctx);

        canvas.addEventListener('mousedown',function(evt){
            document.body.style.mozUserSelect = document.body.style.webkitUserSelect = document.body.style.userSelect = 'none';
            lastX = evt.offsetX || (evt.pageX - canvas.offsetLeft);
            lastY = evt.offsetY || (evt.pageY - canvas.offsetTop);
            dragStart = ctx.transformedPoint(lastX,lastY);
            dragged = false;
        },false);
        canvas.addEventListener('mousemove',function(evt){
            lastX = evt.offsetX || (evt.pageX - canvas.offsetLeft);
            lastY = evt.offsetY || (evt.pageY - canvas.offsetTop);
            dragged = true;
            if (dragStart){
                var pt = ctx.transformedPoint(lastX,lastY);
                ctx.translate(pt.x-dragStart.x,pt.y-dragStart.y);
                reRender();
            }
        },false);
        canvas.addEventListener('mouseup',function(evt){
            dragStart = null;
            if (!dragged) zoom(evt.shiftKey ? -1 : 1 );
        },false);
        var zoom = function(clicks){
            var pt = ctx.transformedPoint(lastX,lastY);
            ctx.translate(pt.x,pt.y);
            var factor = Math.pow(scaleFactor,clicks);
            ctx.scale(factor,factor);
            ctx.translate(-pt.x,-pt.y);
            reRender();
        };
        var handleScroll = function(evt){
            var delta;
            if(evt.detail<0 || evt.wheelDelta>0)delta=zoomFactorDelta;
            else delta=-1*zoomFactorDelta;
            if (delta) zoom(delta);
            return evt.preventDefault() && false;
        };
        canvas.addEventListener('DOMMouseScroll',handleScroll,false);
        canvas.addEventListener('mousewheel',handleScroll,false);

    };

    var drawGrid = function() {
        var i;
        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.lineWidth = 1;
        var offsetX=0, offsetY=0;
        if(renderOptions["moveModel"]){
            offsetX = offsetModelX;
            offsetY = offsetModelY;
        }

        ctx.beginPath();
        for(i=0;i<=gridSizeX;i+=gridStep){
            ctx.moveTo(i*zoomFactor-offsetX, 0-offsetY);
            ctx.lineTo(i*zoomFactor-offsetX, -gridSizeY*zoomFactor-offsetY);
        }
        ctx.stroke();

        ctx.beginPath();
        for(i=0;i<=gridSizeY;i+=gridStep){
            ctx.moveTo(0-offsetX, -i*zoomFactor-offsetY);
            ctx.lineTo(gridSizeX*zoomFactor-offsetX, -i*zoomFactor-offsetY);
        }
        ctx.stroke();

    };

    var drawLayer = function(layerNum, fromProgress, toProgress, isNextLayer){
        var i, speedIndex= 0;

        isNextLayer = typeof isNextLayer !== 'undefined' ? isNextLayer : false;
        if (!isNextLayer) {
            layerNumStore=layerNum;
            progressStore = {from: fromProgress, to: toProgress};
        }

        if (!model || !model[layerNum]) return;

        var cmds = model[layerNum];
        var x, y;

        if (fromProgress > 0) {
            prevX = cmds[fromProgress-1].x * zoomFactor;
            prevY = -cmds[fromProgress-1].y * zoomFactor;
        } else if (fromProgress === 0 && layerNum == 0) {
            if (model[0] && model[0].x !== undefined && model[0].y !== undefined) {
                prevX = model[0].x * zoomFactor;
                prevY = -model[0].y * zoomFactor;
            } else {
                prevX = 0;
                prevY = 0;
            }
        } else if(typeof(cmds[0].prevX) !== 'undefined' && typeof(cmds[0].prevY) !== 'undefined') {
            prevX = cmds[0].prevX * zoomFactor;
            prevY = -cmds[0].prevY * zoomFactor;
        } else {
            if (model[layerNum-1]) {
                prevX = undefined;
                prevY = undefined;
                for (i = model[layerNum-1].length-1; i >= 0; i--) {
                    if (prevX === undefined && model[layerNum-1][i].x !== undefined) prevX = model[layerNum-1][i].x * zoomFactor;
                    if (prevY === undefined && model[layerNum-1][i].y !== undefined) prevY =- model[layerNum-1][i].y * zoomFactor;
                }
                if (prevX === undefined) prevX=0;
                if (prevY === undefined) prevY=0;
            } else {
                prevX = 0;
                prevY = 0;
            }
        }

        for (i = fromProgress; i <= toProgress; i++) {
            ctx.lineWidth = 1;

            if (typeof(cmds[i]) === 'undefined') continue;

            if (typeof(cmds[i].prevX) !== 'undefined' && typeof(cmds[i].prevY) !== 'undefined') {
                prevX = cmds[i].prevX * zoomFactor;
                prevY = -cmds[i].prevY * zoomFactor;
            }

            if (typeof(cmds[i].x) === 'undefined' || isNaN(cmds[i].x)) {
                x = prevX / zoomFactor;
            } else {
                x = cmds[i].x;
            }
            if (typeof(cmds[i].y) === 'undefined' || isNaN(cmds[i].y)) {
                y=prevY/zoomFactor;
            } else {
                y = -cmds[i].y;
            }

            var alpha = renderOptions['showNextLayer'] && isNextLayer ? 0.5 : 1.0;
            var shade = cmds[i].tool * 0.15;
            if (!cmds[i].extrude && !cmds[i].noMove) {
                if (cmds[i].retract == -1) {
                    if (renderOptions["showRetracts"]) {
                        ctx.strokeStyle = pusher.color(renderOptions["colorRetract"]).shade(shade).alpha(alpha).html();
                        ctx.fillStyle = pusher.color(renderOptions["colorRetract"]).shade(shade).alpha(alpha).html();
                        ctx.beginPath();
                        ctx.arc(prevX, prevY, renderOptions["sizeRetractSpot"], 0, Math.PI*2, true);
                        ctx.stroke();
                        ctx.fill();
                    }
                }
                if(renderOptions["showMoves"]){
                    ctx.strokeStyle = pusher.color(renderOptions["colorMove"]).shade(shade).alpha(alpha).html();
                    ctx.beginPath();
                    ctx.moveTo(prevX, prevY);
                    ctx.lineTo(x*zoomFactor,y*zoomFactor);
                    ctx.stroke();
                }
            } else if(cmds[i].extrude) {
                if (cmds[i].retract == 0) {
                    ctx.strokeStyle = pusher.color(renderOptions["colorLine"][cmds[i].tool]).alpha(alpha).html();
                    ctx.lineWidth = renderOptions['extrusionWidth'];
                    ctx.beginPath();
                    ctx.moveTo(prevX, prevY);
                    ctx.lineTo(x*zoomFactor,y*zoomFactor);
                    ctx.stroke();
                } else {
                    if (renderOptions["showRetracts"]) {
                        ctx.strokeStyle = pusher.color(renderOptions["colorRestart"]).shade(shade).alpha(alpha).html();
                        ctx.fillStyle = pusher.color(renderOptions["colorRestart"]).shade(shade).alpha(alpha).html();
                        ctx.beginPath();
                        ctx.arc(prevX, prevY, renderOptions["sizeRetractSpot"], 0, Math.PI*2, true);
                        ctx.stroke();
                        ctx.fill();
                    }
                }
            }
            prevX = x * zoomFactor;
            prevY = y * zoomFactor;
        }
        ctx.stroke();
    };


// ***** PUBLIC *******
    return {
        init: function(){
            startCanvas();
            initialized = true;
            ctx.translate(10,gridSizeY*zoomFactor+20);
        },
        setOption: function(options){
            for(var opt in options){
                if(options.hasOwnProperty(opt))renderOptions[opt] = options[opt];
            };

            if(initialized)reRender();
        },
        getOptions: function(){
            return renderOptions;
        },
        debugGetModel: function(){
            return model;
        },
        render: function(layerNum, fromProgress, toProgress){
            if(!initialized)this.init();
            if(!model){
                drawGrid();
            }else{
                if(layerNum < model.length){
                    var p1 = ctx.transformedPoint(0, 0);
                    var p2 = ctx.transformedPoint(canvas.width, canvas.height);
                    ctx.clearRect(p1.x, p1.y, p2.x - p1.x, p2.y - p1.y);
                    drawGrid();
                    if(renderOptions['showNextLayer'] && layerNum < model.length - 1) {
                        drawLayer(layerNum+1, 0, this.getLayerNumSegments(layerNum+1), true);
                    }
                    drawLayer(layerNum, fromProgress, toProgress);
                }else{
                    console.log("Got request to render non-existent layer");
                }
            }
        },
        getModelNumLayers: function(){
            return model?model.length:1;
        },
        getLayerNumSegments: function(layer){
            if(model){
                return model[layer]?model[layer].length:1;
            }else{
                return 1;
            }
        },
        doRender: function(mdl, layerNum){
            var mdlInfo;
            model = mdl;
            prevX=0;
            prevY=0;
            if(!initialized)this.init();

            mdlInfo = GCODE.gCodeReader.getModelInfo();
            speeds = mdlInfo.speeds;
            speedsByLayer = mdlInfo.speedsByLayer;
            offsetModelX = (gridSizeX/2-(mdlInfo.min.x+mdlInfo.modelSize.x/2))*zoomFactor;
            offsetModelY = (mdlInfo.min.y+mdlInfo.modelSize.y/2)*zoomFactor-gridSizeY/2*zoomFactor;
            if(ctx)ctx.translate(offsetModelX, offsetModelY);

            if (!model[layerNum]) return;
            this.render(layerNum, 0, model[layerNum].length);
        },
        getZ: function(layerNum){
            if(!model&&!model[layerNum]){
                return '-1';
            }
            var cmds = model[layerNum];
            for(var i=0;i<cmds.length;i++){
                if(cmds[i].prevZ!==undefined)return cmds[i].prevZ;
            }
            return '-1';
        }

}
}());
