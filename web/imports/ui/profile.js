import './profile.html';
import { Meteor } from 'meteor/meteor';
import { Observations } from '../api/observations.js';

Template.profile.helpers({
    user() {
	return Meteor.user();
    },
    numPending(user) {
	if (user) {
	    return Observations.find({'owner': user._id,
				      'completed': false}).count();
	}
    },
    numCompleted(user) {
	if (user) {
	    return Observations.find({'owner': user._id,
				      'completed': true}).count();
	}
    },

    badges(user) {
	if (user) {
	    return ['Explorer', ' Kronian', ' Harperian'];
	}
    }, 
});
