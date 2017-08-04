import { Meteor } from 'meteor/meteor';
import { Mongo } from 'meteor/mongo';
import { check } from 'meteor/check';

export const Announcements = new Mongo.Collection('announcements');

// publish announcements
if (Meteor.isServer) {
    // create publication
    Meteor.publish('announcements', function() {
	return Announcements.find();
    });
}

Meteor.methods({
    'announcements.insert'(title, text) {

	// validate they are both strings
	check(title, String)
	check(text, String)

	if (! Roles.userIsInRole(this.userId, 'admin')) {
	    throw new Meteor.Error('not-authorized');
	}

	// insert into collection
	Announcements.insert({
	    title: title,
	    text: text,
	    date: new Date(), 
	});
    }
});
