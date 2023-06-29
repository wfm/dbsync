Some thoughts on what I've been doing with Mary Joy's website

# Wordpress
In WP, everything is a post. Posts are posts, pages are posts, events are posts, products are post, orders are posts, etc. The venues for events are separate posts. And on and on. Dr. Codd would be disappointed by this arrangement. It is flexible but keeping everything in one homogonous has severe drawbacks. It makes working with "staging" sites damn near impossible. While I am changing the content on the staging site (creating and modifying posts), customers are creating orders on the prod site (creating and modifying more posts). And we're creating events and new products on the prod site.

Post types on our site:
* attachment
* custom_css
* elementor_library
* jb_store_css
* nav_menu_item
* page
* post
* product
* revision
* rl_gallery
* shop_order
* sp_wps_shortcodes
* tribe_events
* tribe_venue
* wcpcsu-custom-post
* wp_global_styles
* wpforms

## What I've Tried

I wrote an elaborate program to compare the SQL to recreate the database and generate a script to add changes from prod to the staging site tables. I got pretty close to something usable. 

## What could be better about that

It might be easier to push changes from the staging DB to the prod DB.

WP has a kitchen sink _options table. It's simply a key, value store. It would be helpful to know when a value was updated. Maybe I could add a separate table with the keys and a timestamp that is updated via a trigger.

The staging idea is a kludge. WP stores a lot of data with the site URL, with keys to other tables (mainly _posts), and [something else]. You have to edit all that data when you try to sync.

## What I'd like
I'd like to work on a copy of the prod site on my local machine. The Local app seems to work well for that purpose. Coupled with the paid version of WP Migrate, you can pull changes from the local site into prod. However, that doesn't handle orders, events, etc.

It would be nice to keep everything (reasonably static) in Git.

## WP-based alternatives

Limiting the _posts table to posts and pages would be an improvement. Events, products and orders would have their own normalized sets of tables. Maybe there are plugins that work this way? Syncing the database would be easier, but still have room for errors.

# Alternative to WP

Some alternatives:
* Shopify. The cost was a turnoff at the beginning, $480/year to start.
* Shopify alternatives, like BigCommerce, Ecwid
* https://www.forbes.com/advisor/business/software/best-shopify-alternatives/
* Squarespace, Wix
* Etsy or similar for the craft stuff. They have high fees.
* There are art-specific sites for the abstract paintings.
* DIY system. This is appealing in that it would be interesting to build.
