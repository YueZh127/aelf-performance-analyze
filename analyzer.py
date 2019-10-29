#! /usr/bin/python3

import datetime


class Analyzer(object):
    def __init__(self, endpoint):
        self.endpoint = endpoint

    generate_blocks = {}
    valid_blocks = {}
    invalid_blocks = {}
    continue_blocks = {}
    lib_hash_list = {}

    # warn and error messages
    warn_msgs = {
        "warn1": "Switch Longest chain",
        "warn2": "Block validate fails before execution",
        "warn3": "Mining canceled because best chain already updated",
        "warn4": "cannot get block hash",
    }
    error_msgs = {
        "err1": "Error during discover",
        "err2": "Time slot already passed before execution",
        "err3": "Sender produced too many continuous blocks",
        "err4": "Execution cancelled",
        "err5": "Request chain 2113 failed"
    }

    begin = 0
    end = 0

    @staticmethod
    def read_file_line(file_name):
        with open(file_name, 'r') as f:
            while True:
                line = f.readline()
                if not line:
                    break
                yield line

    @staticmethod
    def file_line_count(file):  # 读取文件行数
        count = -1
        for count, line in enumerate(open(file, 'rU')):
            pass
        count += 1

        return count

    def parse_blocks(self, block_file, low_height, high_height):
        print("=>analyze blocks")

        start_height = 0
        end_height = 0

        lines = Analyzer.read_file_line(block_file)
        for line in lines:
            message = line.split(" ")
            time = message[0] + ' ' + message[1]
            current_hash = message[2]
            height = int(message[3])
            if low_height != 0 and height < low_height:
                continue
            if high_height != 0 and height > high_height:
                break

            previous_hash = message[4]
            executed_txs = int(str(message[5]).replace(",", ""))
            canceled_txs = int(message[6])

            block_info = {'time': time, 'height': height, 'hash': current_hash, 'previous': previous_hash,
                          'executed_txs': executed_txs, 'canceled_txs': canceled_txs}
            self.generate_blocks[str(height)] = block_info

            if start_height == 0:
                start_height = height
                end_height = height
            elif end_height == height - 1:
                end_height += 1
            else:
                number = str(len(self.continue_blocks) + 1)
                continue_info = {"start": start_height, "end": end_height, "blocks": end_height - start_height + 1}
                self.continue_blocks[number] = continue_info
                start_height = height
                end_height = height

        self.begin = int(sorted(self.generate_blocks.keys())[0])
        self.end = int(sorted(self.generate_blocks.keys())[len(self.generate_blocks) - 1])
        print('start time: {0}'.format(self.generate_blocks[str(self.begin)]['time']))
        print('end time: {0}'.format(self.generate_blocks[str(self.end)]['time']))
        print('generated blocks: {0}'.format(len(self.generate_blocks)))
        print('generated blocks round: {0}'.format(len(self.continue_blocks)))
        print()

    def parse_libs(self, lib_file, low_height, high_height):
        print('=>analyze libs')
        lines = Analyzer.read_file_line(lib_file)
        for line in lines:
            message = line.split(" ")
            time = message[0] + ' ' + message[1]
            height = int(str(message[2]).replace(",", ""))
            lib_hash = message[3].replace("\n", "")

            if low_height != 0 and height < low_height:
                continue
            if high_height != 0 and height > high_height:
                break

            lib_info = {'time': time, 'hash': lib_hash}
            self.lib_hash_list[str(height)] = lib_info
        # update height based on lib
        sorted_keys = sorted(self.lib_hash_list.keys())
        begin = int(sorted_keys[0])
        end = int(sorted_keys[len(sorted_keys) - 1])
        if begin > self.begin:
            self.begin = begin
        if end < self.end:
            self.end = end
        # analyze block timespan
        begin_date = datetime.datetime.strptime(self.lib_hash_list[str(begin)]['time'], '%Y-%m-%d %H:%M:%S,%f')
        end_date = datetime.datetime.strptime(self.lib_hash_list[str(end)]['time'], '%Y-%m-%d %H:%M:%S,%f')
        time_span = (end_date - begin_date).seconds
        print('lib height from: {0}~{1}'.format(self.begin, self.end))
        print('lib time: {0}~{1}'.format(self.lib_hash_list[str(begin)]['time'], self.lib_hash_list[str(end)]['time']))
        print('average second/block: {0}s'.format(round(time_span / (self.end - self.begin), 3)))
        print()

    def analyze_blocks(self):
        print("=>analyze block")

        generated_keys = self.generate_blocks.keys()
        for height in range(self.begin, self.end):
            height_key = str(height)
            if height_key in generated_keys:
                if self.generate_blocks[height_key]['hash'] == self.lib_hash_list[height_key]:
                    self.valid_blocks[height_key] = self.generate_blocks[height_key]
                else:
                    self.invalid_blocks[height_key] = self.generate_blocks[height_key]
        valid_no = len(self.valid_blocks)
        invalid_no = len(self.invalid_blocks)
        total_no = len(self.generate_blocks)
        print('valid blocks:{0}, forked blocks: {1}, none lib blocks: {2}'
              .format(valid_no, invalid_no, (total_no - valid_no - invalid_no)))
        if total_no != 0:
            print('forked block percent: {0}%'.format(round(invalid_no * 100 / total_no, 2)))
        print()

    def analyze_continue_blocks(self):
        print("=>analyze continue blocks")
        enough_no = 0
        standard_no = 0
        less_no = 0
        for number in self.continue_blocks:
            block = self.continue_blocks[number]
            if block['blocks'] > 8:
                enough_no += 1
                # print('blocks: {0}~{1}, count: {2}'.format(block['start'], block['end'], block['blocks']))
            elif block['blocks'] == 8:
                standard_no += 1
            else:
                less_no += 1
                # print('blocks: {0}~{1}, count: {2}'.format(block['start'], block['end'], block['blocks']))

        print('average each round generated blocks: {0}'.format(
            round(len(self.generate_blocks) / len(self.continue_blocks), 2)))
        print('standard: {0}, more blocks: {1}, less blocks: {2}'.format(standard_no, enough_no, less_no))
        print()

    def analyze_node_txs(self):
        print("=>analyze node transactions")
        executed_amounts = 0
        canceled_amounts = 0
        count = len(self.generate_blocks)
        for height in self.generate_blocks:
            block_info = self.generate_blocks[height]
            executed_amounts += block_info['executed_txs']
            canceled_amounts += block_info['canceled_txs']

        print('total executedTxs: {0}, canceledTxs: {1}'.format(executed_amounts, canceled_amounts))
        if count != 0:
            print('average each block executed txs: {0}, canceled txs: {1}'.format(round(executed_amounts / count, 2),
                                                                                   round(canceled_amounts / count, 2)))
        print()

    def parse_warn(self, warn_log):  # 分析警告信息行数
        print("=>analyze warn log")
        warn_summary = {}
        for key in self.warn_msgs.keys():
            warn_summary[key] = 0

        lines = Analyzer.read_file_line(warn_log)
        count = Analyzer.file_line_count(warn_log)
        print("total warn message line: {0}".format(count))

        for line in lines:
            for key in self.warn_msgs.keys():
                if self.warn_msgs[key] in line:
                    warn_summary[key] += 1
                    break

        other_warn = count
        for key in warn_summary:
            other_warn -= warn_summary[key]
            print('type={0}, count={1}'.format(self.warn_msgs[key], warn_summary[key]))
        print('type=others, count={0}'.format(other_warn))
        print()

    def parse_error(self, error_log):  # 分析错误信息行数
        print("=>analyze error log")
        error_summary = {}
        for key in self.error_msgs.keys():
            error_summary[key] = 0

        lines = Analyzer.read_file_line(error_log)
        count = Analyzer.file_line_count(error_log)
        print("total error message line: {0}".format(count))
        for line in lines:
            for key in self.error_msgs.keys():
                if self.error_msgs[key] in line:
                    error_summary[key] += 1
                    break

        other_error = count
        for key in error_summary:
            other_error -= error_summary[key]
            print('type={0}, count={1}'.format(self.error_msgs[key], error_summary[key]))
        print('type=others, count={0}'.format(other_error))
        print()
