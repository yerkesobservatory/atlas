import './home.html';

import { Meteor } from 'meteor/meteor';
import { Announcements } from '../api/announcements.js';

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
