LandmarkRegistration
====================

An interactive registration tool that manages viewing and manipulating of sets of fiducials


This is a work-in-progress that will ultimately be an extension or core module of 3D Slicer.

Some background information is here:

http://www.na-mic.org/Wiki/index.php/2013_Summer_Project_Week:Landmark_Registration

Installation
============

To test: You need to checkout two repositories (1) this one and (2) https://github.com/pieper/CompareVolumes

If you checked them out to /tmp, then you can start slicer as follows:

Linux: 

 ./Slicer --additional-module-paths /tmp/CompareVolumes /tmp/LandmarkRegistration
 
(on windows you run "Slicer.exe <args>" from a console.  On mac, you use "open Slicer.app <args>")

Use
===

Linear:
# load the two volumes to register
# enter the LandmarkRegistration module
# select Fixed and Moving (do not select transformed)
# scroll to the Registration area and select Linear
# enable the Registration Active checkbox (this will create a transformed volume)
# pick Axi/Sag/Cor in the Visualization box (this will create a custom layout with fixed on top, moving in the middle, and fixed + transformed on the bottom)
# place a fiducial on either the fixed or moving volumes (a corresponding one will be created on the other volume)
# drag the fiducials in the fixed and moving volumes until they are on the same anatomical location.  The blended view will update automatically on mouse release.
# place and adjust fiducials until registration is good.
# Option: Similarity mode is Rigid + Scale and can be good for some cross-subject registration

Caveats
=======
* Affine mode requires more landmarks but should work
* Thin-Plate spline mode works but does not automatically update (click Apply to calculate).  It overwrites the transformed volume so you can't go back to Linear mode from Thin-Plate mode).
* Hybrid B-Spline mode is still under development.
