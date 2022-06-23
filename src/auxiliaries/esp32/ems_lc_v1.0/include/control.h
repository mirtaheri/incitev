#define kI 1
#define kD 1

int *PDReg(int *X)
{
	//float derivation[9];
    static int derivation[9];

    //for(int i=0; i==sizeof(X)/4; i++)
    //    X[i]=121;

    for(int i=sizeof(X)/4; i>0; i--){
        derivation[i]=X[i]-X[i-1];
        //Serial.println(derivation[i]);
    }
    return derivation;
}

float Filter(float xk, float xf_k, float kfilt)
{
    
    xf_k+= kfilt * (xk-xf_k);

    return xf_k;
}