import { Template } from 'meteor/templating';

import { Observations } from '../api/observations.js';

import './body.html';

Template.body.helpers({
    observations() {
	return Observations.find({});
    },
});
