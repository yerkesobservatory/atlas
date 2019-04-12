import $ from 'jquery';
// create a new validator to check for a taget string or valid RA/DEC
$.validator.addMethod("validCoordinate", function(value, element) {
    var check_length=0;
    var solar_system = ['mercury','venus','moon','mars','jupiter','saturn','uranus','neptune','pluto']
    // if string contains :,+ or - then we assume that it is a RA/Dec string
    if ((value.indexOf(':') > -1)){// || (value.indexOf('+') > -1) || (value.indexOf('-') > -1)) {
        // we assume that we have RA/Dec
        // this checks for the following forms
        // 00:00:00 +-00:00:00
        // 00:00:00 +-00:00:00.00
        // 00:00:00.00 +-00:00:00
        // 00:00:00.00 +-00:00:00.00
        // 00h00m00s +-00d00m00s
        // 00h00m00s +-00d00m00.00s
        // 00h00m00.00s +-00d00m00s
        // 00h00m00.00s +-00d00m00.00s

        re = /\d{1,2}[h:]\d{1,2}[m:]\d{1,2}(?:.\d{1,2}){0,1}s{0,1}\s[+-]\d{1,2}[d:]\d{1,2}[m:]\d{1,2}(?:.\d{1,2}){0,1}s{0,1}/;
        if (re.exec(value)) {
            return true;
        }
        else {
            return false;
        }

        // otherwise we assume we don't understand this coordinate system
        return false;
    }

    else if (solar_system.indexOf(String(value).toLowerCase()) >= 0){
        return true;}    
    else{
        var targetIsValid = false;
        $.ajax({
          type: "GET",
          url: "https://simbad.u-strasbg.fr/simbad/sim-id?output.format=ASCII&Ident="+value,
          async: false, //this flag makes the call synchronous, i.e. waits for the HTTP response!
          success: function(result){
            if(result.length > 300) { //300 is the magic number
                targetIsValid = true;
            }
          }
        });
        return targetIsValid;
    }
}, "Invalid target name or RA/Dec pair");
//      else{true_or_false=false;}
                     // else{return false;}
                     //console.log(response.content.length);
                     //if ((simbad_return) > 300) {
                     //        return true;
                     // console.log(simbad_return);}

                    // else{console.log(response.content.length); return false;
        //console.log(simbad_return);
        //return true
        // we assume that we have a target string
        // TODO: lookup target in database to confirm that we understand it
        // Could use a resource server endpoint with astropy so we guarantee that
        // the executor can find this particular target
//      return true_or_false;
//      console.log(true_or_false);
//      return true;
//    }
//    return false;
//}, "Invalid target name or RA/Dec pair");
