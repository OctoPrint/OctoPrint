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
+ "G1 Z15 F9000 ;move the platform down 15mm\n"
+ "G92 E0 ;zero the extruded length\n"
+ "G1 F200 E5.5 ;extrude 5mm of feed stock\n"
+ "G92 E0 ;zero the extruded length again\n"
+ "G92 E0 ;zero the extruded length again\n"
+ "G1 F9000\n"
+ "G90 ;absolute positioning\n";

settings["printer.endcode"] =  "G91 ;relative positioning\n"
+ "G1 E-2 F300 ;retract the filament a bit before lifting the nozzle, to release some of the pressure\n"
+ "G1 Z+0.5 E-4 X-20 Y-20 F9000 ;move Z up a bit and retract filament even more\n"
+ "G28 X0 Y0 ;move X/Y to min endstops, so the head is out of the way\n"
+ "M107 ;fan off\n"
+ "M84 ;disable axes / steppers\n"
+ "G90 ;absolute positioning\n";

settings["printer.speed"] = 10;
//normalSpeed = speed;
settings["printer.bottomLayerSpeed"] = 10;
settings["printer.firstLayerSlow"] = false;
settings["printer.bottomFlowRate"] = 2;
settings["printer.travelSpeed"] = 120;
settings["printer.filamentThickness"] = 8;
settings["printer.wallThickness"] = 0.7;
settings["printer.screenToMillimeterScale"] = 1;
settings["printer.layerHeight"] = 0.7;
settings["printer.temperature"] = 40;
settings["printer.bed.temperature"] = 0;
settings["printer.useSubLayers"] = true;
settings["printer.enableTraveling"] = true;
settings["printer.retraction.enabled"] = true;
settings["printer.retraction.speed"] = 50;
settings["printer.retraction.minDistance"] = 5;
settings["printer.retraction.amount"] = 5;
settings["printer.heatup.temperature"] = 0;
settings["printer.heatup.bed.temperature"] = 0;
settings["printer.dimensions.x"] = 100;
settings["printer.dimensions.y"] = 100;
settings["printer.dimensions.z"] = 100;