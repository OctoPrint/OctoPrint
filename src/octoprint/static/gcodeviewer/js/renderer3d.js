/**
 * User: hudbrog (hudbrog@gmail.com)
 * Date: 10/21/12
 * Time: 4:59 PM
 */
GCODE.renderer3d = (function(){
// ***** PRIVATE ******
    var modelLoaded=false;
    var model;
    var prevX=0, prevY= 0, prevZ=0;
    var sliderHor, sliderVer;
    var object;
    var geometry;

    var WIDTH = 650, HEIGHT = 630;
    var VIEW_ANGLE = 70,
        ASPECT = WIDTH / HEIGHT,
        NEAR = 0.1,
        FAR = 10000;

    var renderer;
    var scene;
    var camera = new THREE.PerspectiveCamera(VIEW_ANGLE, ASPECT, NEAR, FAR);
    var controls;
    var halfWidth = window.innerWidth / 2;
    var halfHeight = window.innerHeight / 2;
    var mouseX = 0, mouseY = 0;

    var renderOptions = {
        showMoves: true,
        colorLine: 0x000000,
        colorMove: 0x00ff00,
        rendererType: "webgl"
    };

    var render = function(){
        controls.update();
        renderer.render(scene, camera);
        requestAnimationFrame(render);
    };


    var buildModelIteration = function(layerNum){
        var j;
        var cmds  = model[layerNum];
        if(!cmds)return;
        for(j=0;j<cmds.length;j++){
            if(!cmds[j])continue;
            if(!cmds[j].x)cmds[j].x=prevX;
            if(!cmds[j].y)cmds[j].y=prevY;
            if(!cmds[j].z)cmds[j].z=prevZ;
            if(!cmds[j].extrude){
            }
            else {
                geometry.vertices.push( new THREE.Vector3(prevX, prevY, prevZ));
                geometry.vertices.push( new THREE.Vector3(cmds[j].x, cmds[j].y, cmds[j].z));
            }
            prevX = cmds[j].x;
            prevY = cmds[j].y;
            prevZ = cmds[j].z;
        }
    };

    var buildModelIteratively = function(){
        var i;

        for(i=0;i<model.length;i+=1){
            buildModelIteration(i);
            //TODO: need to remove UI stuff from here

        }
        var lineMaterial = new THREE.LineBasicMaterial({color: renderOptions["colorLine"], lineWidth: 2, opacity: 0.6, fog: false});
        geometry.computeBoundingBox();
        object.add(new THREE.Line(geometry, lineMaterial, THREE.LinePieces));
        var center = new THREE.Vector3().add(geometry.boundingBox.min, geometry.boundingBox.max).divideScalar(2);
        object.position = center.multiplyScalar(-1);

    }

    var buildModel = function(){
        var i,j;
        var cmds = [];

        for(i=0;i<model.length;i++){
            cmds = model[i];
            if(!cmds)continue;
            for(j=0;j<cmds.length;j++){
                if(!cmds[j])continue;
                if(!cmds[j].x)cmds[j].x=prevX;
                if(!cmds[j].y)cmds[j].y=prevY;
                if(!cmds[j].z)cmds[j].z=prevZ;
                if(!cmds[j].extrude){
                }
                else {
                    geometry.vertices.push( new THREE.Vector3(prevX, prevY, prevZ));
                    geometry.vertices.push( new THREE.Vector3(cmds[j].x, cmds[j].y, cmds[j].z));
                }
                prevX = cmds[j].x;
                prevY = cmds[j].y;
                prevZ = cmds[j].z;
            }
//TODO: need to remove UI stuff from here
            $(function() {
                $( "#progressbar" ).progressbar({
                    value: i/model.length*100
                });
            });

        }
        var lineMaterial = new THREE.LineBasicMaterial({color: renderOptions["colorLine"], lineWidth: 4, opacity: 1, fog: false});
        geometry.computeBoundingBox();
        object.add(new THREE.Line(geometry, lineMaterial, THREE.LinePieces));
        var center = new THREE.Vector3().add(geometry.boundingBox.min, geometry.boundingBox.max).divideScalar(2);
        object.position = center.multiplyScalar(-1);
    };

    var debugAxis = function(axisLength){
        //Shorten the vertex function
        function v(x,y,z){
            return new THREE.Vector3(x,y,z);
        }

        //Create axis (point1, point2, colour)
        function createAxis(p1, p2, color){
            var line, lineGeometry = new THREE.Geometry(),
                lineMat = new THREE.LineBasicMaterial({color: color, lineWidth: 1});
            lineGeometry.vertices.push(p1, p2);
            line = new THREE.Line(lineGeometry, lineMat);
            scene.add(line);
        }

        createAxis(v(-axisLength, 0, 0), v(axisLength, 0, 0), 0xFF0000);
        createAxis(v(0, -axisLength, 0), v(0, axisLength, 0), 0x00FF00);
        createAxis(v(0, 0, -axisLength), v(0, 0, axisLength), 0x0000FF);
    };


// ***** PUBLIC *******
    return {
        init: function(){
            modelLoaded = false;
            if(renderOptions["rendererType"]=="webgl")renderer = new THREE.WebGLRenderer({clearColor:0xffffff, clearAlpha: 1});
            else if(renderOptions["rendererType"]=="canvas")renderer = new THREE.CanvasRenderer({clearColor:0xffffff, clearAlpha: 1});
            else { console.log("unknown rendererType"); return;}

            scene = new THREE.Scene()
            var $container = $('#3d_container');
            camera.position.z = 200;
            scene.add(camera);
            renderer.setSize(WIDTH, HEIGHT);
            $container.empty();
            $container.append(renderer.domElement);

            controls = new THREE.TrackballControls(camera);
            controls.rotateSpeed = 1.0;
            controls.zoomSpeed = 1.2;
            controls.panSpeed = 0.8;

            controls.noZoom = false;
            controls.noPan = false;

            controls.staticMoving = true;
            controls.dynamicDampingFactor = 0.3;

            controls.keys = [ 65, 83, 68 ];

        },
        isModelReady: function(){
            return modelLoaded;
        },
        setOption: function(options){
            for(var opt in options){
                if(options.hasOwnProperty(opt))renderOptions[opt] = options[opt];
            }
        },
        setModel: function(mdl){
            model = mdl;
            modelLoaded=false;
        },
        doRender: function(){
//            model = mdl;
            prevX=0;
            prevY=0;
            prevZ=0;
            object = new THREE.Object3D();
            geometry = new THREE.Geometry();
            this.init();
            if(model)modelLoaded=true;
            else return;
//            buildModel();
            buildModelIteratively();

            scene.add(object);
            debugAxis(100);

            var mousemove = function(e){
                mouseX = e.clientX - halfWidth;
                mouseY = e.clientY - halfHeight;
            };
            // Action!
            render();
//            renderer.render(scene, camera);
        }
    }
}());

