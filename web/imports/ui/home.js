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
