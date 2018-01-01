import './telescopes.html';

import { Meteor } from 'meteor/meteor';
import { Telescopes } from '../api/telescopes.js';

// on template creation, subscribe to Telescopes collection
Template.telescopes.onCreated(function onCreated() {
    Meteor.subscribe('telescopes');
});

// helpers for telescopes
Template.telescopes.helpers({
    telescope() {
	return Telescopes.findOne();
    },
    isWeatherGood(telescope) {
	if (telescope) {
	    if (telescope.weather == "GOOD") {
		return "text-success";
	    } else {
		return "text-danger";
	    };
	}
    }, 
});

