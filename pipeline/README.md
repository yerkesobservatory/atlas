# SEOpipeline [![Travis](https://travis-ci.org/yerkesobservatory/SEOpipeline.svg?branch=master)](https://travis-ci.org/yerkesobservatory/SEOpipeline)

### Objectives: 
Develop a working pipeline for the Stone Edge Observatory telescope which will reduce images to a scientific standard, i.e. images calibrated for scientific projects.

### Tasks: 
Here is a proposed set of tasks that need to be completed for a well-functioning pipeline. It follows the same order as the image-reduction program, THELI. We can discuss which parts are most important and need to be finished first. 
	
#### More immediate importance
1. *Initialize*: Make sure the pipeline knows where to retrieve images and how often to check for new images. 
2. *Preparation*: Split multi-extension files if they exist; name/re-name well.
3. *Calibration*:
  * *MasterCalibrationStacks*: Prepare master calibration images (e.g. master flats, darks, biases) and stack most recent multiple exposures (grouped by date), if they exist. This can be part of the Bias, Dark, and Flat steps.
  * *StepBias*: Find most recent biases/master biases stack with the same exposure time as image we’re looking to reduce. Find best match if same exposure time not available.
  * *StepDark*: Find most recent darks/master dark stack with the same exposure time as image we’re looking to reduce. Find best match if same exposure time not available.
  * *StepFlat*: Find most recent flats/master flat stack in the same filter as the image we’re looking to reduce. 
  * *StepCalibrateImage*: Perform master/single bias (subtraction), dark (subtraction), flat (division by normalized to mode) calibration to each   image taken.
  * *StepAstrometry*: Perform astrometry on the reduced images (astrometry.net script)
  * *MasterImageStacks*: Stack (median?) calibrated images of the same filter, exposure, and object taken during a single observing run. Requires 5-10 frames to be statistically significant.                                    
  * *StepHotpix*: Median image stack should take care of this problem, but still run LA cosmic.py stacked image. Make sure parameter file for this program is edited per use. 
  * *StepRgb*: Create an RGB image. Figure out which filters to use for this.
	

#### Less immediate importance
4. *Superflatting*: This is complicated and may not be necessary, but basically taking care of more nuanced things, such as fringing and airglow
5. *Weighting*: Do we want weight images? Probably not necessary, but just in case.  
 Master flats are sensitivity maps. Also taking care of satellite tracks,   
 ghosts, edge effects/vignetting, etc. Bad pixels could be set to 0.
6. *Astrom/Photom*: Perform calibrations on the objects based on SDSS magnitudes (Lindsay’s project). Should we do this for each image to get more data for these photometry projects?
7. *Coaddition*: Subtract individual sky models from each exposure. If we have weighted images/want to make mosaics. “Resampling kernels, output pixel scale, proper motion vector for moving targets.”

