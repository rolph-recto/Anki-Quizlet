#-------------------------------------------------------------------------------
# Name:        Quizlet plugin for Anki
# Purpose:     Import decks from Quizlet.com into Anki
#
# Author:      Rolph Recto
#
# Created:     12/06/2012
# Copyright:   (c) Rolph Recto 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__window = None

import sys
import math
import time
import datetime as dt
import urllib as url
import urllib2 as url2
import json

#Anki
from aqt import mw
from aqt.qt import *

#PyQT
from PyQt4.QtGui import *
from PyQt4.Qt import Qt

class QuizletWindow(QWidget):
    PAGE_FIRST       = 1
    PAGE_PREVIOUS    = 2
    PAGE_NEXT        = 3
    PAGE_LAST        = 4
    RESULT_ERROR     = -1
    RESULTS_PER_PAGE = 50
    __APIKEY         = "ke9tZw8YM6" #used to access Quizlet API

    """main window of Quizlet plugin; shows search results"""
    def __init__(self):
        super(QuizletWindow, self).__init__()

        self.results = None
        self.thread = None
        self.name = ""
        self.user = ""
        self.result_page = -1

        self.initGUI()

    def initGUI(self):
        """create the GUI skeleton"""

        self.box_top = QVBoxLayout()
        self.box_upper = QHBoxLayout()

        #left side
        self.box_left = QVBoxLayout()

        #name field
        self.box_name = QHBoxLayout()
        self.label_name = QLabel("Name")
        self.text_name = QLineEdit("",self)

        self.box_name.addWidget(self.label_name)
        self.box_name.addWidget(self.text_name)

        #user field
        self.box_user = QHBoxLayout()
        self.label_user = QLabel("User")
        self.text_user = QLineEdit("",self)

        self.box_user.addWidget(self.label_user)
        self.box_user.addWidget(self.text_user)

        #add layouts to left
        self.box_left.addLayout(self.box_name)
        self.box_left.addLayout(self.box_user)

        #right side
        self.box_right = QVBoxLayout()

        #sort type
        self.box_sort = QHBoxLayout()
        self.label_sort = QLabel("Sort by:", self)
        self.buttongroup_sort = QButtonGroup()
        self.radio_popularity = QRadioButton("Popularity", self)
        self.radio_name = QRadioButton("Name", self)
        self.radio_date = QRadioButton("Date modified", self)
        self.radio_popularity.setChecked(True)
        self.buttongroup_sort.addButton(self.radio_popularity)
        self.buttongroup_sort.addButton(self.radio_name)
        self.buttongroup_sort.addButton(self.radio_date)

        self.box_sort.addWidget(self.label_sort)
        self.box_sort.addWidget(self.radio_popularity)
        self.box_sort.addWidget(self.radio_name)
        self.box_sort.addWidget(self.radio_date)
        self.box_sort.addStretch(1)

        #sort order
        self.box_sortorder = QHBoxLayout()
        self.label_sortorder = QLabel("Sort order:", self)
        self.buttongroup_sortorder = QButtonGroup()
        self.radio_descending = QRadioButton("Descending", self)
        self.radio_ascending = QRadioButton("Ascending", self)
        self.radio_descending.setChecked(True)
        self.buttongroup_sortorder.addButton(self.radio_ascending)
        self.buttongroup_sortorder.addButton(self.radio_descending)

        self.box_sortorder.addWidget(self.label_sortorder)
        self.box_sortorder.addWidget(self.radio_descending)
        self.box_sortorder.addWidget(self.radio_ascending)
        self.box_sortorder.addStretch(1)

        #search button
        self.box_search = QHBoxLayout()
        self.button_search = QPushButton("Search", self)

        self.box_search.addStretch(1)
        self.box_search.addWidget(self.button_search)

        self.button_search.clicked.connect(self.onSearch)

        #add layouts to right
        self.box_right.addLayout(self.box_sort)
        self.box_right.addLayout(self.box_sortorder)

        #add left and right layouts to upper
        self.box_upper.addLayout(self.box_left)
        self.box_upper.addSpacing(20)
        self.box_upper.addLayout(self.box_right)

        #table navigation
        self.box_tablenav = QHBoxLayout()

        self.button_first = QPushButton("<<", self)
        self.button_first.setMaximumWidth(30)
        self.button_first.setVisible(False)

        self.button_previous = QPushButton("<", self)
        self.button_previous.setMaximumWidth(30)
        self.button_previous.setVisible(False)

        self.result_page = 1
        self.button_current = QPushButton(str(self.result_page), self)
        self.button_current.setMaximumWidth(50)
        self.button_current.setVisible(False)

        self.button_next = QPushButton(">", self)
        self.button_next.setMaximumWidth(30)
        self.button_next.setVisible(False)

        self.button_last = QPushButton(">>", self)
        self.button_last.setMaximumWidth(30)
        self.button_last.setVisible(False)

        self.box_tablenav.addStretch(1)
        self.box_tablenav.addWidget(self.button_first)
        self.box_tablenav.addWidget(self.button_previous)
        self.box_tablenav.addWidget(self.button_current)
        self.box_tablenav.addWidget(self.button_next)
        self.box_tablenav.addWidget(self.button_last)
        self.box_tablenav.addStretch(1)

        self.button_first.clicked.connect(self.onPageFirst)
        self.button_previous.clicked.connect(self.onPagePrevious)
        self.button_current.clicked.connect(self.onPageCurrent)
        self.button_next.clicked.connect(self.onPageNext)
        self.button_last.clicked.connect(self.onPageLast)

        #results label
        self.label_results = QLabel("")

        #table of results
        self.table_results = QTableWidget(2, 4, self)
        self.table_results.setHorizontalHeaderLabels(["Name", "User",
            "Items", "Date modified"])
        self.table_results.verticalHeader().hide()
        self.table_results.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_results.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_results.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_results.horizontalHeader().setSortIndicatorShown(False)
        self.table_results.horizontalHeader().setClickable(False)
        self.table_results.horizontalHeader().setResizeMode(QHeaderView.Interactive)
        self.table_results.horizontalHeader().setStretchLastSection(True)
        self.table_results.horizontalHeader().setMinimumSectionSize(100)
        self.table_results.verticalHeader().setResizeMode(QHeaderView.Fixed)
        self.table_results.setMinimumHeight(275)
        self.table_results.setVisible(False)

        #import selected deck
        self.box_import = QHBoxLayout()
        self.button_import = QPushButton("Import Deck", self)
        self.button_import.setVisible(False)

        self.box_import.addStretch(1)
        self.box_import.addWidget(self.button_import)

        #add all widgets to top layout
        self.box_top.addLayout(self.box_upper)
        self.box_top.addLayout(self.box_search)
        self.box_top.addLayout(self.box_tablenav)
        self.box_top.addWidget(self.label_results)
        self.box_top.addWidget(self.table_results)
        self.box_top.addLayout(self.box_import)
        self.setLayout(self.box_top)

        self.setMinimumWidth(500)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setWindowTitle("Import from Quizlet")
        self.show()

    def onSearch(self):
        """user clicked search button; load first page of results"""
        self.name = self.text_name.text()
        self.user = self.text_user.text()
        self.fetchResults()

    def onPageFirst(self):
        """first page button clicked"""
        self.__changePage(QuizletWindow.PAGE_FIRST)

    def onPagePrevious(self):
        """first page button clicked"""
        self.__changePage(QuizletWindow.PAGE_PREVIOUS)


    def onPageCurrent(self):
        """let user jump to any page"""
        page, ok = QInputDialog.getInteger(self, "Jump to Page",
            "What page? ({0} - {1})".format(1, self.results["total_pages"]),
            1, 1, self.results["total_pages"])

        if ok:
            self.fetchResults(page)

    def onPageNext(self):
        """first page button clicked"""
        self.__changePage(QuizletWindow.PAGE_NEXT)

    def onPageLast(self):
        """first page button clicked"""
        self.__changePage(QuizletWindow.PAGE_LAST)

    def __changePage(self, change):
        """determine what page to fetch"""
        if change == QuizletWindow.PAGE_FIRST:
            self.fetchResults(1)
        elif change == QuizletWindow.PAGE_PREVIOUS:
            if self.result_page - 1 >= 1:
                self.fetchResults(self.result_page-1)
        elif change == QuizletWindow.PAGE_NEXT:
            if self.result_page + 1 <= self.results["total_pages"]:
                self.fetchResults(self.result_page+1)
        elif change == QuizletWindow.PAGE_LAST:
            self.fetchResults( self.results["total_pages"] )

    def showTable(self, show=True):
        """set results table visible/invisible"""
        self.button_first.setVisible(show)
        self.button_previous.setVisible(show)
        self.button_current.setVisible(show)
        self.button_next.setVisible(show)
        self.button_last.setVisible(show)
        self.table_results.setVisible(show)
        self.button_import.setVisible(show)

    def hideTable(self):
        """make results table invisible"""
        self.showTable(False)

    def loadResultsToTable(self):
        """insert data from results dict into table widget"""
        #clear table first
        self.table_results.setRowCount(0)
        deckList = self.results["sets"]

        #iterate through the decks and add them to the table
        for index in range(len(deckList)):
            if index+1 > self.table_results.rowCount():
                self.table_results.insertRow(index)

            #deck name
            name = QTableWidgetItem(deckList[index]["title"])
            name.setToolTip(deckList[index]["title"])
            self.table_results.setItem(index, 0, name)

            #user who created deck
            user = QTableWidgetItem(deckList[index]["created_by"])
            user.setToolTip(deckList[index]["created_by"])
            self.table_results.setItem(index, 1, user)

            #number of items in the deck
            items = QTableWidgetItem(str(deckList[index]["term_count"]))
            items.setToolTip(str(deckList[index]["term_count"]))
            self.table_results.setItem(index, 2, items)

            #last date that the deck was modified
            date_str = time.strftime("%m/%d/%Y",
                time.localtime(deckList[index]["modified_date"]))
            date = QTableWidgetItem(date_str)
            date.setToolTip(date_str)
            self.table_results.setItem(index, 3, date)

    def fetchResults(self, page=1):
        """load results"""
        global __APIKEY

        self.results = None
        self.hideTable()
        self.label_results.setText("Searching for \"{0}\" ..."
            .format(self.name))

        #build search URL
        if not self.user == "":
            search_url = ("https://api.quizlet.com/2.0/search/sets"
                  "?q={0}"
                  "&creator={1}"
                  "&page={2}"
                  "&per_page={3}"
                  "&client_id={4}")
        else:
            search_url = ("https://api.quizlet.com/2.0/search/sets"
                  "?q={0}"
                  "&page={2}"
                  "&per_page={3}"
                  "&client_id={4}")

        search_url = search_url.format(self.name, self.user, page,
            QuizletWindow.RESULTS_PER_PAGE, QuizletWindow.__APIKEY)

        #stop the previous thread first
        if not self.thread == None:
            self.thread.terminate()

        #download the data!
        self.thread = QuizletDownloader(self, search_url)
        self.thread.start()

        while not self.thread.isFinished():
            mw.app.processEvents()
            self.thread.wait(50)

        self.results = self.thread.results

        #error with fetching data; don't display table
        if self.thread.error:
            self.setPage(QuizletWindow.RESULT_ERROR)
        #everything went through!
        else:
            self.setPage(page)
            self.loadResultsToTable()
            self.showTable()

    def setPage(self, page):
        """set page of results to load"""
        if page == QuizletWindow.RESULT_ERROR:
            self.result_page = -1
            self.button_current.setText(" ")
            self.label_results.setText( ("No results found!") )
        else:
            first = ((page-1)*50)+1
            last = page*QuizletWindow.RESULTS_PER_PAGE
            num_results = self.results["total_results"]
            self.result_page = page
            self.button_current.setText(str(page))
            self.label_results.setText( ("Displaying results {0} - {1} of {2}."
                .format(first, last, num_results)) )
            self.table_results.verticalHeader().setOffset(first)

class QuizletDownloader(QThread):
    """thread that downloads results from the Quizlet API"""

    def __init__(self, window, url):
        super(QuizletDownloader, self).__init__()
        self.window=window
        self.url = url
        self.error = False
        self.results = None

    def run(self):
        """run thread; download results!"""
        try:
            self.results = json.loads(url2.urlopen(self.url).read())
        except url2.URLError:
            self.error = True


def runQuizletPlugin():
    """menu item pressed; display search window"""
    global __window
    __window = QuizletWindow()

#create menu item
action = QAction("Import from Quizlet", mw)
mw.connect(action, SIGNAL("triggered()"), runQuizletPlugin)
mw.form.menuTools.addAction(action)