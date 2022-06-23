

//Vector in stationary abc frame
typedef struct { float t;
				 float t_1;
				 float t_2;
				 float t_3;
			   } Meter;

//Vector in stationary alpha-beta frame			   
typedef struct { float alpha;
				 float beta;
			   } Xalphabeta;
			   
//Vector in stationary alpha-beta frame + amplitude			   
typedef struct { float alpha;
				 float beta;
				 float amp;
			   } Xalphabeta_amp;

//Vector in (d,q) frame 
typedef struct { float d;
				 float q;
			   } Xdq;

//Acquisition vector 
typedef struct { float ch0;
			   	 float ch1;
			   	 float ch2;
			   	 float ch3;
			   } Xin; 	

//Sine and cosine
typedef struct { float sin;
				 float cos;
			   } Xsc;

//PI regulator parameters structure
typedef struct { float kp;
				 float ki;
				 float lim;
			   } XPIRegPars;

//PI regulator variables structure
typedef struct { float ref;
				 float out;
				 float fbk;
				 float err;
				 float prop;
				 float intg;
			    } XPIRegVars;