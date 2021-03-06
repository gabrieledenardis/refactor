# -*- coding: utf-8 -*-
# !/usr/bin/env python

# PyQt4 imports
from PyQt4 import QtCore

# Python imports
from threading import Event
import struct
import os

# Project imports
import index_header_reader
import cache_address
import cache_entry


class OperaAnalyzer(QtCore.QObject):
    """Analyzer for Opera cache.
    """

    # Signals
    signal_update_table_preview = QtCore.pyqtSignal(int, int, str, str, str, str)
    signal_finished = QtCore.pyqtSignal()

    def __init__(self, parent=None, input_path=None):
        super(OperaAnalyzer, self).__init__(parent)

        # Input path to analyze
        self.input_path = input_path
        # List of all cache entries found
        self.list_cache_entries = []

        # Thread stopped by user
        self.stopped_by_user = False
        # Analysis running
        self.worker_is_running = True

        # Signal from "button_stop_analysis"
        self.signal_stop = Event()

    def analyze_cache(self):
        """Analyzing an Opera cache input path updating a list with all entries found.
        Also sending signals to update "table_analysis_preview" with values for found entries.
        :return: nothing
        """

        # Opera "index" file
        index_file = os.path.join(self.input_path, "index")

        # Address table size and number of entries in "index" file
        table_size = index_header_reader.read_index_header(index_file)["table_size"]
        num_entries = index_header_reader.read_index_header(index_file)["number_of_entries"]

        # Header dimension for "index" file
        index_header_dimension = 368

        with open(index_file, "rb") as f_index:
            # Skipping header
            f_index.seek(index_header_dimension)

            # Addresses table in "index" file
            for address in range(table_size):
                # "Button_stop_analysis" clicked
                if self.signal_stop.is_set():
                    self.stopped_by_user = True
                    self.worker_is_running = False
                    break

                # Binary address (32 bits)
                bin_address_in_index = format(struct.unpack("<I", f_index.read(4))[0], "032b")

                # Existing and valid entry
                if bin_address_in_index and bin_address_in_index[0] == "1":
                    # Entry location
                    cache_file_instance = cache_address.CacheAddress(
                        binary_address=bin_address_in_index,
                        cache_path=self.input_path
                    )

                    cache_entry_instance = cache_entry.CacheEntry(
                        cache_path=self.input_path,
                        entry_file=cache_file_instance.file_path,
                        block_dimension=cache_file_instance.block_dimension,
                        block_number=cache_file_instance.block_number
                    )

                    # If an entry has a valid next entry address (an entry with the same hash),
                    # adding it to the entries list. Those entries are not in "index table addresses"
                    while cache_entry_instance.next_entry_address != 0:
                        if (cache_entry_instance.data_stream_addresses[0] is not None and
                                isinstance(cache_entry_instance.data_stream_addresses[0].resource_data, dict)):

                            # Updating "table_analysis_preview"
                            self.signal_update_table_preview.emit(
                                len(self.list_cache_entries) - 1,
                                num_entries,
                                str(cache_entry_instance.key_hash),
                                cache_entry_instance.key_data,
                                cache_entry_instance.data_stream_addresses[0].resource_data.get('Content-Type', '-'),
                                cache_entry_instance.creation_time
                            )

                        # Not HTTP Header
                        else:
                            # Updating "table_analysis_preview"
                            self.signal_update_table_preview.emit(
                                len(self.list_cache_entries)-1,
                                num_entries,
                                str(cache_entry_instance.key_hash),
                                cache_entry_instance.key_data,
                                " - ",
                                cache_entry_instance.creation_time
                            )

                        # Updating "list_cache_entries"
                        self.list_cache_entries.append(cache_entry_instance)

                        # Next entry address (from current entry)
                        bin_next_entry_address = format(cache_entry_instance.next_entry_address, "032b")

                        # Corresponding entry location (from next entry address)
                        cache_next_file_instance = cache_address.CacheAddress(
                            binary_address=bin_next_entry_address,
                            cache_path=self.input_path
                        )

                        cache_entry_instance = cache_entry.CacheEntry(
                            cache_path=self.input_path,
                            entry_file=cache_next_file_instance.file_path,
                            block_dimension=cache_next_file_instance.block_dimension,
                            block_number=cache_next_file_instance.block_number
                        )

                    # Updating "list_cache_entries"
                    self.list_cache_entries.append(cache_entry_instance)

                    # Resuming addresses table
                    if (cache_entry_instance.data_stream_addresses[0] is not None and
                            isinstance(cache_entry_instance.data_stream_addresses[0].resource_data, dict)):

                        # Updating "table_analysis_preview"
                        self.signal_update_table_preview.emit(
                            len(self.list_cache_entries) - 1,
                            num_entries,
                            str(cache_entry_instance.key_hash),
                            cache_entry_instance.key_data,
                            cache_entry_instance.data_stream_addresses[0].resource_data.get('Content-Type', '-'),
                            cache_entry_instance.creation_time
                        )

                    # Not HTTP Header
                    else:
                        # Updating "table_analysis_preview"
                        self.signal_update_table_preview.emit(
                            len(self.list_cache_entries) - 1,
                            num_entries,
                            str(cache_entry_instance.key_hash),
                            cache_entry_instance.key_data,
                            "-",
                            cache_entry_instance.creation_time
                        )

        # Analysis terminated
        self.worker_is_running = False
        self.signal_finished.emit()
