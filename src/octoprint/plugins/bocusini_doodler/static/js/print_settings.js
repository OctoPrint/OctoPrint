settings = {};

settings["printer.type"] = "";
settings["printer.startcode"] = ";Generated with Doodle3D (default)\n"
+ "M109 S{printingTemp} ;set target temperature \n"
+ ";{if heatedBed}M190 ;S{printingBedTemp} ;set target ;bed temperature\n"
+ "G21 ;metric values\n"
+ "G91 ;relative positioning\n"
+ ";M107 ;start with the fan off\n"
+ "G28 X0 Y0 ;move X/Y to min endstops\n"
+ "G28 Z0 ;move Z to min endstops\n"
// + "G1 Z1 F9000 ;move the platform down 15mm\n" //original 15
+ "G92 E0 ;zero the extruded length\n"
+ "G1 F200 E1.5 ;extrude 1.5mm of feed stock\n" // original 5.5
+ "G92 E0 ;zero the extruded length again\n"
+ "G92 E0 ;zero the extruded length again\n"
+ "G1 F6000\n"
+ "G90 ;absolute positioning\n";

settings["printer.endcode"] =  "G91 ;relative positioning\n"
+ "G1 E-1 F300 ;retract the filament a bit before lifting the nozzle, to release some of the pressure\n"
+ "G1 Z+0.5 E-1 X-20 Y-20 F9000 ;move Z up a bit and retract filament even more\n"
+ "G28 X0 Y0 ;move X/Y to min endstops, so the head is out of the way\n"
+ "M107 ;fan off\n"
+ "M84 ;disable axes / steppers\n"
+ "G90 ;absolute positioning\n";

settings["printer.speed"] = 10;
//normalSpeed = speed;
settings["printer.bottomLayerSpeed"] = 10;
settings["printer.firstLayerSlow"] = false;
settings["printer.bottomFlowRate"] = 1; //zuletzt 2
settings["printer.travelSpeed"] = 120;
settings["printer.filamentThickness"] = 15; //zuletzt 8
settings["printer.wallThickness"] = 0.5;
settings["printer.screenToMillimeterScale"] = 0.23 //original 1.0
settings["printer.layerHeight"] = 0.5;
settings["printer.temperature"] = 40;
settings["printer.bed.temperature"] = 0;
settings["printer.useSubLayers"] = false; //original true
settings["printer.enableTraveling"] = true;
settings["printer.retraction.enabled"] = true;
settings["printer.retraction.speed"] = 50;
settings["printer.retraction.minDistance"] = 3;
settings["printer.retraction.amount"] = 1;
settings["printer.heatup.temperature"] = 0;
settings["printer.heatup.bed.temperature"] = 0;
settings["printer.dimensions.x"] = 100;
settings["printer.dimensions.y"] = 100;
settings["printer.dimensions.z"] = 100;