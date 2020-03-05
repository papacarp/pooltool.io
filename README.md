# pooltool.io
A public repo to keep track of issues and feature requests in pooltool


# Using ptwidget.html

![ptwidget](ptwidget.png)

To get a widget like this on your website, and insert the html into your website page.  Make sure you update the title of the table and your pool id first as well.  Note that the height reported is the PoolTool majority max height, not your own pool's height.  

Note the includes of Jquery and numeral.

If anyone would like to beautify the simple formatting or optimize this as a widget please let me know.  lifetime blocks will get added next time I'm updating the back end.

# Using send_slots.sh

You can now submit your upcoming slots to pooltool. (under active development)  

You have two options:
1.  You can send just your slot count.  This will be displayed along side your epoch blocks in pooltool.
2.  You can send your slot count plus validation for the previous epoch.  If you validate your block count submissions we can then display ACTUAL performance metrics for your pool.  Your data will also be used to develop high level statistics on assignments vs. stake.

There are two methods offered at this time for validation:
1.  You can send your slots encrypted at the start of the epoch along with your slot count.  Then at the start of the next epoch you will send a key to allow us to unencrypt the slots and verify your loaded count matches the actual. (we are testing the final version of this today)
2.  You can send a hash of your leader logs at the start of the epoch along with your slot count. Then at the start of the next epoch you will send us the actual leader logs and confirm the hash matchees what you sent previously. (In development - we have not finished implementing this yet)

If the hash or encryption do not match pooltool will not allow you to upload your slots.  Eventually we will implement probation for pools that upload erroneous data.
