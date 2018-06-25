import './home.html';

import { Meteor } from 'meteor/meteor';
import { Tracker } from 'meteor/tracker';
import { Announcements } from '../api/announcements.js';
import { Observations } from '../api/observations.js';
import { Telescopes } from '../api/telescopes.js';
import $ from 'jquery';


Template.announcements.onCreated(function onCreated() {
    Meteor.subscribe('announcements');
});

Template.announcements.helpers({
    announcements() {
	return Announcements.find();
    },
    prettifyDate(date) {
	return date.toISOString().split('T')[0]
    },
});

Template.home.helpers({
    changeBackground(img) {
	$('body').css("background-image", img);
	$('body').css("background", img);
    },
});

// we wish to update background based upon weather
// this will automatically run as Telescope is changed
Tracker.autorun(function () {
    const scope = Telescopes.findOne();
    if (scope) {
	// current sun altitude
	sun = scope.weather.sun;
	cloud = scope.weather.cloud;
	rain = scope.weather.rain;

	// extract current background name
	// var url = $('body').css('background');
	// const currentWeather = url.split('.gif')[0].split('_').pop();

	// // check if its rainy
	// if (rain > 0) {
	//     url = url.replace(currentWeather, 'rain');
	//     $('body').css('background', url);
	// }
	// // cloud
	// else if (cloud > 0.3) {
	//     url = url.replace(currentWeather, 'cloud');
	//     $('body').css('background', url);
	// }
	// // daytime
	// if (sun > 5) {
	//     url = url.replace(currentWeather, 'sun');
	//     $('body').css('background', url);
	// }
	// // sunset/sunrise
	// else if ((sun <= 5) && (sun >= -5)) {
	//     url = url.replace(currentWeather, 'sunset');
	//     $('body').css('background', url);
	// }
	// // we show some stars
	// else {
	//     url = url.replace(currentWeather, 'stars');
	//     $('body').css('background', url);
	// }
    }
});


Template.history.helpers({
  settings: function() {
    return {
      rowsPerPage: 10,
      showNavigationRowsPerPage: false,
      multiColumnSort: false,
      showNavigation: "never",
      showFilter: false,
      fields: [
        {key:'', label:'Start Time'},
        {key:'', label:'End Time'},
        {key:'', label:'Object'},
        {key:'', label:'Priority'},
        {key:'', label:'Exposure'},
        {key:'', label:'Errors'}]
    }
  },
});

//intro.js walkthrough
Template.body.onRendered(
	function() { setTimeout(function() { 
		if (RegExp('multipage=2', 'gi').test(window.location.search)) {
			var intro = introJs();
          intro.setOptions({
            steps: [
              { 
              	element: document.querySelector('#form-program'), 
                intro: 'First, select one of the pre-set observing programs...(You can create you own program later.) Click on "next" when you are ready.'
              },
              { 
              	element: document.querySelector('#form-target'), 
                intro: 'Then tell us what you want to observe. How about M78?'
              },
              { 
              	element: document.querySelector('#advanced-options'), 
                intro: 'Want to try more advanced settings?'
              },
              { 
              	element: document.querySelector('#submit_obs'), 
                intro: 'Submit when you are ready! Click "next" to continue' ,
              },
              { 
              	element: document.querySelector('#programs'), 
                intro: 'Remember the program that you select for your observation? Learn more details from here... Click "Next page" to continue' ,
              },
            ]
          });

            intro.setOption('doneLabel', 'Next page').start().oncomplete(function() { 
			window.location.href = 'programs?multipage=3';});
        }
        else if (RegExp('multipage=3', 'gi').test(window.location.search)){
        	var intro = introJs();
          intro.setOptions({
            steps: [
              { 
              	element: document.querySelector('#program_intro'), 
                intro: 'Click on each later to learn details about the pre-set programs',
              },
              { 
              	element: document.querySelector('#new_program_div'), 
                intro: 'Create your own program from here.',
              },
              { 
              	element: document.querySelector('#sessions'), 
                intro: 'Visit SESSIONS to reserve telescope time for even more advanced observing! Click "Next page" to continue.'
              }
            ]
          });
        	intro.setOption('disableInteraction', true).setOption('doneLabel', 'Next page').start().oncomplete(function() { 
			window.location.href = 'sessions?multipage=4';});
        }
        else if (RegExp('multipage=4', 'gi').test(window.location.search)){
        	var intro = introJs();
        	intro.setOptions({
        		steps: [
        		{  
                intro: 'So here\'s the page for reserving sessions.'
              	},
              	{ 
                intro: 'That\'s all for the walkthrough! If you forget anything, come back to your home page to run it again at anytime.'
              	},
        		]
        	});
			intro.setOption('doneLabel', 'Back to home').start().oncomplete(function() { 
			window.location.href = 'home';});
        }
    }, 2500);});


Template.home.events({
	'click #button_wlkt':
	function() { 
        	var intro = introJs();
          	intro.setOptions({
            steps: [
              { 
                intro: 'Welcome to Stone Edge Observatory home page! Ready to explore?'
              },
              { 
              	element: document.querySelector('#step2'), 
                intro: 'Checkout the current status of the observatory here. Is the slit open now?'
              },
              { 
              	element: document.querySelector('#step3'), 
                intro: 'Your observations will be listed here',
                position: 'left'
              },
              { 
              	element: document.querySelector('#observations'), 
                intro: 'Now click here learn to submit your first observation! Select "SUBMIT AN OBSERVATION" in the dropdown bar and press "next step" to continue.' ,
                position: 'right'
              }
            ]
          });

          intro.setOption('doneLabel', 'Next page').start().oncomplete(function() { 
			window.location.href = 'newObservation?multipage=2';});
    },
  'click #button_side':
  function () {
    document.getElementById("mySidenav").style.width = "750px";
    document.getElementById("main").style.marginLeft = "750px";
  },
  'click #close_side':
  function () {
    document.getElementById("mySidenav").style.width = "0";
    document.getElementById("main").style.marginLeft = "0";
}
});
