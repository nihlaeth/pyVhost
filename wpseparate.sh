#!/bin/bash
if [ $# -lt 3 ]
then
    echo "Used for separating wordpress multi-site enabled blogs."
    echo "Do NOT use for separating main blog if you don't know what you're doing!"
    echo "Usage: `basename $0` user database pattern"
    echo "Eg: `basename $0` root mydatabase wp_2_%"
    exit 1
fi
user=$1
database=$2
pattern=$3

# pattern used for separate out non-main blogs
mysqldump -h '127.0.0.1' -u $user -p $database wp_users `mysql -u $user -p -ND $database -e "SHOW TABLES LIKE '$pattern'" | awk '{printf $1" "}'` > dbdump-$pattern-`date "+%Y-%m-%d-%H-%M"`.sql

# pattern I used to separate out main blog - this leaves the multi-site specific tables behind. Does not pick up on plugin tables automatically!
# not like does not work with show tables, and the table scheme trick did not work for unknown reasons. so this is the hacky way.

#mysqldump -h '127.0.0.1' -u $user -p $database wp_commentmeta wp_comments wp_customcontactforms_field_options wp_customcontactforms_fields wp_customcontactforms_forms wp_customcontactforms_styles wp_customcontactforms_user_data wp_itsec_lockouts wp_itsec_log wp_itsec_temp wp_links wp_options wp_postmeta wp_posts wp_slim_browsers wp_slim_content_info wp_slim_events wp_slim_outbound wp_slim_screenres wp_slim_stats wp_slim_stats_3 wp_slim_stats_archive wp_slim_stats_archive_3 wp_term_relationships wp_term_taxonomy wp_terms wp_usermeta wp_users > dbdump-wpmain-`date "+%Y-%m-%d-%H-%M"`.sql

