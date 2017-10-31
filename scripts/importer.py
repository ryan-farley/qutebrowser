#!/usr/bin/env python3
# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014-2017 Claude (longneck) <longneck@scratchbook.ch>
# Copyright 2014-2017 Florian Bruhin (The Compiler) <mail@qutebrowser.org>

# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.


"""Tool to import data from other browsers.

Currently only importing bookmarks from Netscape Bookmark files is supported.
"""


import argparse

browser_default_input_format = {
    'chromium': 'netscape',
    'ie': 'netscape',
    'firefox': 'netscape',
    'seamonkey': 'netscape',
    'palemoon': 'netscape'
}


# pylint: disable=too-many-branches
def main():
    args = get_args()
    bookmark_types = []
    output_format = None
    input_format = args.input_format
    if args.search_output:
        bookmark_types = ['search']
        if args.oldconfig:
            output_format = 'oldsearch'
        else:
            output_format = 'search'
    else:
        if args.bookmark_output:
            output_format = 'bookmark'
        elif args.quickmark_output:
            output_format = 'quickmark'
        if args.import_bookmarks:
            bookmark_types.append('bookmark')
        if args.import_keywords:
            bookmark_types.append('keyword')
    # Select defaults more intelligently than argparse
    if not bookmark_types:
        bookmark_types = ['bookmark', 'keyword']
    if not output_format:
        output_format = 'quickmark'
    if not input_format:
        if args.browser:
            input_format = browser_default_input_format[args.browser]
        else:
            #default to netscape
            input_format = 'netscape'

    import_function = {'netscape': import_netscape_bookmarks}
    import_function[input_format](args.bookmarks, bookmark_types,
                                  output_format)


def get_args():
    """Get the argparse parser."""
    parser = argparse.ArgumentParser(
        epilog="To import bookmarks from Chromium, Firefox or IE, "
        "export them to HTML in your browsers bookmark manager. ")
    parser.add_argument(
        'browser',
        help="Which browser? {%(choices)s}",
        choices=browser_default_input_format.keys(),
        nargs='?',
        metavar='browser')
    parser.add_argument(
        '-i',
        '--input-format',
        help='Which input format? (overrides browser default; "netscape" if '
        'neither given)',
        choices=set(browser_default_input_format.values()),
        required=False)
    parser.add_argument(
        '-b',
        '--bookmark-output',
        help="Output in bookmark format.",
        action='store_true',
        default=False,
        required=False)
    parser.add_argument(
        '-q',
        '--quickmark-output',
        help="Output in quickmark format (default).",
        action='store_true',
        default=False,
        required=False)
    parser.add_argument(
        '-s',
        '--search-output',
        help="Output config.py search engine format (negates -B and -K)",
        action='store_true',
        default=False,
        required=False)
    parser.add_argument(
        '--oldconfig',
        help="Output search engine format for old qutebrowser.conf format",
        default=False,
        action='store_true',
        required=False)
    parser.add_argument(
        '-B',
        '--import-bookmarks',
        help="Import plain bookmarks (can be combiend with -K)",
        action='store_true',
        default=False,
        required=False)
    parser.add_argument(
        '-K',
        '--import-keywords',
        help="Import keywords (can be combined with -B)",
        action='store_true',
        default=False,
        required=False)
    parser.add_argument('bookmarks', help="Bookmarks file (html format)")
    args = parser.parse_args()
    return args


def search_escape(url):
    """Escape URLs such that preexisting { and } are handled properly.

    Will obviously trash a properly-formatted Qutebrowser URL.
    """
    return url.replace('{', '{{').replace('}', '}}')


def import_netscape_bookmarks(bookmarks_file, bookmark_types, output_format):
    """Import bookmarks from a NETSCAPE-Bookmark-file v1.

    Generated by Chromium, Firefox, IE and possibly more browsers. Not all
    export all possible bookmark types:
        - Firefox mostly works with everything
        - Chrome doesn't support keywords at all; searches are a separate
          database
    """
    import bs4
    with open(bookmarks_file, encoding='utf-8') as f:
        soup = bs4.BeautifulSoup(f, 'html.parser')
    bookmark_query = {
        'search': lambda tag: (
            (tag.name == 'a') and
            ('shortcuturl' in tag.attrs) and
            ('%s' in tag['href'])),
        'keyword': lambda tag: (
            (tag.name == 'a') and
            ('shortcuturl' in tag.attrs) and
            ('%s' not in tag['href'])),
        'bookmark': lambda tag: (
            (tag.name == 'a') and
            ('shortcuturl' not in tag.attrs) and
            (tag.string)),
    }
    output_template = {
        'search': {
            'search':
            "c.url.searchengines['{tag[shortcuturl]}'] = "
            "'{tag[href]}' #{tag.string}"
        },
        'oldsearch': {
            'search': '{tag[shortcuturl]} = {tag[href]} #{tag.string}',
        },
        'bookmark': {
            'bookmark': '{tag[href]} {tag.string}',
            'keyword': '{tag[href]} {tag.string}'
        },
        'quickmark': {
            'bookmark': '{tag.string} {tag[href]}',
            'keyword': '{tag[shortcuturl]} {tag[href]}'
        }
    }
    bookmarks = []
    for typ in bookmark_types:
        tags = soup.findAll(bookmark_query[typ])
        for tag in tags:
            if typ == 'search':
                tag['href'] = search_escape(tag['href']).replace('%s', '{}')
            if tag['href'] not in bookmarks:
                bookmarks.append(
                    output_template[output_format][typ].format(tag=tag))
    for bookmark in bookmarks:
        print(bookmark)


if __name__ == '__main__':
    main()
