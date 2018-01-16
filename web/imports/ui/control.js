import './control.html';
import { Meteor } from 'meteor/meteor';
import { Telescopes } from '../api/telescopes.js';

Template.control.onCreated(function onCreated() {
    Meteor.subscribe('telescopes');
});

// helpers for telescopes
Template.control.helpers({
    telescope() {
	return Telescopes.findOne();
},
});
