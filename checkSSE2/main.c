#include <stdlib.h>
#include <stdio.h>

//Read CPU flags, and return 0 if we support SSE2, else return 1
//See: http://en.wikipedia.org/wiki/CPUID#EAX.3D1:_Processor_Info_and_Feature_Bits

int main(int argc, char** argv)
{
	int features;
	
	//Read the CPU features.
	asm("mov $1, %%eax\n"
		"cpuid\n"
		"mov %%edx, %0"
		: "=r"(features) : : "%eax", "%edx", "%ecx");
	
	//Check bit 26, this indicates SSE2 support
	if (features & (1 << 26))
		return 0;
	return 1;
}