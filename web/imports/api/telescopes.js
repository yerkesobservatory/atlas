import { Meteor } from 'meteor/meteor';
import { Mongo } from 'meteor/mongo';

export const Telescopes = new Mongo.Collection('telescopes');

// publish the telescope collection
if (Meteor.isServer) {
    // create the publication
    Meteor.publish('telescopes', function() {
	return Telescopes.find({});
    });
}


