#!/usr/bin/env casperjs

# Copyright (c) 2014, Richard Mortier <mort@cantab.net>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

system = require 'system'
fs = require 'fs'
utils = require 'utils'

casper = require('casper').create({
  clientScripts:  [
    './jquery-2.1.1.min.js'
  ],

  logLevel: "warning",
  verbose: "false",

  viewportSize: { width: 800, height: 600 },
  pageSettings: {
    loadImages: false,
    loadPlugins: false
  },

  userAgent: '''Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/537.4 (KHTML, like Gecko) Chrome/22.0.1229.79 Safari/537.4'''
})

## lib imports
{dbg, remotelog} = require './libmort.coffee'

## error handling, debugging
casper.on 'remote.alert', (msg) -> remotelog "alert", msg
casper.on 'remote.message', (msg) -> remotelog "msg", msg
casper.on 'remote.error', (msg) -> remotelog "error", msg

goog_scrape = (author) ->
  entry = $("#gs_ccl > .gs_r").eq(0).contents(".gs_ri")
  if $(entry).length > 0
    title = $(entry).contents("h3.gs_rt").text()
    console.log "TITLE:'#{title}'"

    cites = $(entry).contents(".gs_fl").text().match("Cited by ([0-9]+)")
    cites = if cites?.length > 0 then cites[1]
    console.log "CITES:'#{cites}'"

    wos = $(entry).contents(".gs_fl").text().match("Web of Science: ([0-9]+)")
    wos = if wos?.length > 0 then wos[1]
    console.log "WOS:'#{wos}'"

    {
      title: $.trim(title)
      cites: $.trim(cites)
      wos: $.trim(wos)
      authors: ""
      venue: ""
    }

scrape = (outfile, errfile, author_raw, author, title_raw, title, oid) ->

  goog_base_uri = "http://scholar.google.co.uk/scholar"
  goog_query = "as_q=#{title}&as_occt=title&as_sauthors=#{author}"
  goog_uri = "#{goog_base_uri}?#{goog_query}"

  msft_base_uri = "http://academic.research.microsoft.com/Search"
  msft_query = "query=author%3a%28#{author}%29%20#{title}"
  msft_uri = "#{msft_base_uri}?#{msft_query}"

  sites = [
    # ["MSFT", msft_uri, msft_scrape],
    ["GOOG", goog_uri, goog_scrape],
    ]

  casper.then ->
    @each sites, (self, site) ->
      [ svc, uri, scrapefn ] = site
      dbg "URI:'#{uri}'"
      @thenOpen uri, () ->
        @capture "#{infile}-pngs/#{oid}.png"
        rs = @evaluate scrapefn, { author }
        dbg "LAST_RESPONSE:'#{last_response}' RS:'#{JSON.stringify(rs)}'"
        if not rs?
          fs.write errfile,
            "#{oid}\t#{(new Date).toISOString()}\t#{author_raw}\t#{title_raw}\t#{uri}\t#{last_response}\n", "a"

          switch last_response
            when -1, 200
              @waitForSelector 'img#recaptcha_challenge_image',
                ( ->
                  @wait 100, () ->
                    @capture "captcha.png"
                    captcha = raw_input "captcha> "
                    @log "CAPTCHA: #{captcha}"
                    @fill "form[method='get']",
                      { 'recaptcha_response_field': captcha }, true
                    ),
                    ->,
                    5000

            when 403
              @wait 5000, ->

            when 503
              @capture "captcha.png"
              captcha = raw_input "ipv4-captcha> "
              @log "IPV4-CAPTCHA: #{captcha}"
              @fill "form[action='CaptchaRedirect']", { 'captcha': captcha }, true
              last_response = -1

        else
          os = "#{oid}\t#{author_raw.trim()}\t#{title_raw.join('')}"\
            +"\t#{author}\t#{rs.title}\t#{svc}\t#{rs.wos}\t#{rs.cites}"
          # os +=
          # "#{author_raw}\t#{title_raw}\t#{uri}\t#{rs.venue}\t#{rs.citation}"
          os += "\t#{(new Date).toISOString()}\n"
          fs.write outfile, os, "a"

## go!

casper.start -> dbg "starting!"

inputs = system.stdin.read()
casper.each (i for i in inputs.split("\n") when i isnt ''), (self, input) ->
  @wait 3000, () ->
    [count, domain, rest...] = input.trim().split(" ")

    uri = "https://domain.opendns.com/#{domain}"
    @thenOpen uri, () ->
      tags = @evaluate (() ->
        $("h3 span.normal").text()
      ), {}
      console.log "#{count} | #{domain} | #{tags.trim()}"

casper.run -> casper.exit()
