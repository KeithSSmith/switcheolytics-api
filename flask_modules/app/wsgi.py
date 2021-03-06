""" index file for REST APIs using Flask """
import json
import time
import datetime
import os
import requests
from datetime import timezone
from flask import Flask, jsonify, make_response, send_from_directory, request
from flask_cors import CORS, cross_origin
from switcheo.switcheo_client import SwitcheoClient
from blockchain.neo.switcheo import SwitcheoSmartContract

app = Flask(__name__)
app.config.from_object(__name__)
cors = CORS(app, resources={r'/*': {"origins": '*'}})
CORS(app)

url_dict = {
    'main': 'https://api.switcheo.network',
    'test': 'https://test-api.switcheo.network',
}

rpc_hostname = os.environ['NEO_RPC_HOSTNAME']
rpc_port = os.environ['NEO_RPC_PORT']
rpc_tls = False
mongodb_protocol = 'mongodb'
mongodb_user = os.environ['MONGODB_USER']
mongodb_password = os.environ['MONGODB_PASSWORD']
mongodb_hostname = os.environ['MONGODB_HOSTNAME']
mongodb_port = os.environ['MONGODB_PORT']
mongodb_db = os.environ['MONGODB_DB']

ssc = SwitcheoSmartContract(rpc_hostname=rpc_hostname,
                            rpc_port=rpc_port,
                            rpc_tls=rpc_tls,
                            mongodb_protocol=mongodb_protocol,
                            mongodb_user=mongodb_user,
                            mongodb_password=mongodb_password,
                            mongodb_hostname=mongodb_hostname,
                            mongodb_port=mongodb_port,
                            mongodb_db=mongodb_db)


def sort_dicts(collection, key_name, sort_key, exclude_keys=[]):
    collection_dict = {}
    collection_rows = ssc.ni.mongo_db[collection].find({key_name: {'$ne': None}})

    for row in collection_rows:
        for asset in row[key_name].keys():
            if asset in exclude_keys:
                continue
            asset_dict = {
                'address': row['_id'],
                sort_key: row[key_name][asset]
            }
            if asset not in collection_dict:
                collection_dict[asset] = []
            collection_dict[asset].append(asset_dict)

    for asset in collection_dict.keys():
        collection_dict[asset] = sorted(collection_dict[asset], key=lambda coin: coin[sort_key], reverse=True)

    return collection_dict


@app.errorhandler(404)
@cross_origin()
def not_found(error):
    """ error handler """
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/')
@cross_origin()
def index():
    """ static files serve """
    return send_from_directory('dist', 'index.html')


@app.route('/switcheo/balance')
@cross_origin()
def switcheo_balance():
    address = request.args.get('address', default=None, type=str)
    network = request.args.get('network', default='main', type=str)
    return get_switcheo_balance(network=network, address=address)


def get_switcheo_balance(network, address):
    sc = SwitcheoClient(switcheo_network=network)
    if address is None:
        return send_from_directory('dist', 'index.html')
    else:
        return str(json.dumps(sc.balance_by_contract(address)))


def get_neoscan_balance(address):
    url = 'https://api.neoscan.io/api/main_net/v1/get_balance/' + address
    params = None
    r = requests.get(url=url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


@app.route('/switcheo/status')
@cross_origin()
def switcheo_status():
    return get_switcheo_status()


def get_switcheo_status():
    status_dict = {
        'switcheo_status': ssc.is_trading_active()
    }
    return str(json.dumps(status_dict))


@app.route('/neo/blockheight')
@cross_origin()
def neo_block_height():
    return get_neo_height()


def get_neo_height():
    height_dict = {
        'neo_blockheight': ssc.get_neo_block_height()
    }
    return str(json.dumps(height_dict))


@app.route('/switcheo/ingested/blockheight')
@cross_origin()
def switcheo_block_height():
    return get_switcheo_height()


def get_switcheo_height():
    height_dict = {
        'switcheo_blockheight': ssc.ni.get_collection_count(collection='blocks') + 2000000
    }
    return str(json.dumps(height_dict))


@app.route('/switcheo/ingested/transactions')
@cross_origin()
def switcheo_transaction_height():
    return get_switcheo_transaction_height()


def get_switcheo_transaction_height():
    height_dict = {
        'switcheo_txn_height': ssc.ni.get_collection_count(collection='transactions')
    }
    return str(json.dumps(height_dict))


@app.route('/switcheo/ingested/fills')
@cross_origin()
def switcheo_fills_height():
    return get_switcheo_fills_height()


def get_switcheo_fills_height():
    height_dict = {
        'switcheo_fee_height': ssc.ni.get_collection_count(collection='fees')
    }
    return str(json.dumps(height_dict))


@app.route('/switcheo/fee/amount')
@cross_origin()
def switcheo_fee_amount():
    return get_switcheo_fee_amount()


def get_switcheo_fee_amount():
    fees_dict = {}
    time_dict = {}
    now_epoch = int(time.time())
    day_epoch = int((datetime.datetime.now() + datetime.timedelta(-1)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['day_epoch'] = day_epoch
    week_epoch = int((datetime.datetime.now() + datetime.timedelta(-7)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['week_epoch'] = week_epoch
    thirty_epoch = int((datetime.datetime.now() + datetime.timedelta(-30)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['thirty_epoch'] = thirty_epoch
    sixty_epoch = int((datetime.datetime.now() + datetime.timedelta(-60)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['sixty_epoch'] = sixty_epoch
    ninety_epoch = int((datetime.datetime.now() + datetime.timedelta(-90)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['ninety_epoch'] = ninety_epoch
    august_epoch = int(datetime.datetime(2018, 8, 1).replace(tzinfo=timezone.utc).timestamp())
    time_dict['august_epoch'] = august_epoch
    january_epoch = int(datetime.datetime(2018, 1, 1).replace(tzinfo=timezone.utc).timestamp())
    time_dict['january_epoch'] = january_epoch

    for key in time_dict:
        fee_asset_dict = {}
        for fee_asset in ssc.ni.mongo_db['fees'].aggregate([
            {
                '$match': {
                    '$and': [
                        {'fee_amount': {'$ne': None}},
                        {'block_time': {'$gte': time_dict[key], '$lte': now_epoch}}
                    ]
                }
            }, {
                '$group': {
                    '_id': {'fee_asset_name': '$fee_asset_name'},
                    'total_fees': {
                        '$sum': '$fee_amount'
                    }
                }
            }
        ]):
            fee_asset_dict[fee_asset['_id']['fee_asset_name']] = fee_asset['total_fees']

        fees_dict[key] = fee_asset_dict

    return str(json.dumps(fees_dict))


@app.route('/switcheo/burnt')
@cross_origin()
def switcheo_burnt():
    return get_switcheo_burnt()


def get_switcheo_burnt():
    switcheo_burned = 0
    fees_dict = {}
    fees_dict['V1'] = 646747 * 100000000
    switcheo_burned += fees_dict['V1']
    null_burned = get_neoscan_balance(address='AFmseVrdL9f9oyCzZefL9tG6UbvhPbdYzM')
    switcheo_burn_address_amount = 0
    for balance in null_burned['balance']:
        asset = balance['asset']
        asset_symbol = balance['asset_symbol']
        if asset == 'Switcheo' and asset_symbol == 'SWTH':
            switcheo_burn_address_amount += int(balance['amount'] * 100000000)
    fees_dict['burn_address'] = switcheo_burn_address_amount
    switcheo_burned += fees_dict['burn_address']

    time_dict = {}
    now_epoch = int(time.time())
    day_epoch = int((datetime.datetime.now() + datetime.timedelta(-1)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['day_epoch'] = day_epoch
    week_epoch = int((datetime.datetime.now() + datetime.timedelta(-7)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['week_epoch'] = week_epoch
    thirty_epoch = int((datetime.datetime.now() + datetime.timedelta(-30)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['thirty_epoch'] = thirty_epoch
    sixty_epoch = int((datetime.datetime.now() + datetime.timedelta(-60)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['sixty_epoch'] = sixty_epoch
    ninety_epoch = int((datetime.datetime.now() + datetime.timedelta(-90)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['ninety_epoch'] = ninety_epoch
    all_epoch = int(datetime.datetime(2018, 1, 1).replace(tzinfo=timezone.utc).timestamp())
    time_dict['all_epoch'] = all_epoch

    fees_dict['V2'] = {}
    fees_dict['V3'] = {}
    for key in time_dict:
        for fee_aggregate in ssc.ni.mongo_db['fees'].aggregate([
            {
                '$match': {
                    '$and': [
                        {'contract_hash_version': 'V2'},
                        {'fee_asset_name': 'SWTH'},
                        {'fee_amount': {'$ne': None}},
                        {'block_time': {'$gte': time_dict[key], '$lte': now_epoch}}
                    ]
                }
            }, {
                '$group': {
                    '_id': {'fee_asset_name': '$fee_asset_name'},
                    'total_fees': {
                        '$sum': '$fee_amount'
                    }
                }
            }
        ]):
            fees_dict['V2'][key] = fee_aggregate['total_fees']
            if key == 'all_epoch':
                switcheo_burned += fee_aggregate['total_fees']

        for fee_aggregate in ssc.ni.mongo_db['fees'].aggregate([
            {
                '$match': {
                    '$and': [
                        {'contract_hash_version': 'V3'},
                        {'taker_fee_burn': True},
                        {'taker_fee_asset_name': 'SWTH'},
                        {'taker_fee_burn_amount': {'$ne': None}},
                        {'block_time': {'$gte': time_dict[key], '$lte': now_epoch}}
                    ]
                }
            }, {
                '$group': {
                    '_id': {'taker_fee_asset_name': '$taker_fee_asset_name'},
                    'total_fees': {
                        '$sum': '$taker_fee_burn_amount'
                    }
                }
            }
        ]):
            fees_dict['V3'][key] = fee_aggregate['total_fees']
            if key == 'all_epoch':
                switcheo_burned += fee_aggregate['total_fees']

    day_amount = 0
    week_amount = 0
    thirty_amount = 0
    sixty_amount = 0
    ninety_amount = 0
    for fee_key in fees_dict:
        if fee_key in ['V2', 'V3']:
            for fee_duration in fees_dict[fee_key]:
                if fee_duration == 'day_epoch':
                    day_amount += fees_dict[fee_key]['day_epoch']
                if fee_duration == 'week_epoch':
                    week_amount += fees_dict[fee_key]['week_epoch']
                if fee_duration == 'thirty_epoch':
                    thirty_amount += fees_dict[fee_key]['thirty_epoch']
                if fee_duration == 'sixty_epoch':
                    sixty_amount += fees_dict[fee_key]['sixty_epoch']
                if fee_duration == 'ninety_epoch':
                    ninety_amount += fees_dict[fee_key]['ninety_epoch']

    fees_dict['all_burnt'] = {}
    fees_dict['all_burnt']['day_epoch'] = day_amount
    fees_dict['all_burnt']['week_epoch'] = week_amount
    fees_dict['all_burnt']['thirty_epoch'] = thirty_amount
    fees_dict['all_burnt']['sixty_epoch'] = sixty_amount
    fees_dict['all_burnt']['ninety_epoch'] = ninety_amount
    fees_dict['all_burnt']['all_epoch'] = switcheo_burned

    return str(json.dumps(fees_dict))


@app.route('/switcheo/fee/count')
@cross_origin()
def switcheo_fee_count():
    return get_switcheo_fee_count()


def get_switcheo_fee_count():
    fees_dict = {}
    time_dict = {}
    now_epoch = int(time.time())
    day_epoch = int((datetime.datetime.now() + datetime.timedelta(-1)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['day_epoch'] = day_epoch
    week_epoch = int((datetime.datetime.now() + datetime.timedelta(-7)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['week_epoch'] = week_epoch
    thirty_epoch = int((datetime.datetime.now() + datetime.timedelta(-30)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['thirty_epoch'] = thirty_epoch
    sixty_epoch = int((datetime.datetime.now() + datetime.timedelta(-60)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['sixty_epoch'] = sixty_epoch
    ninety_epoch = int((datetime.datetime.now() + datetime.timedelta(-90)).replace(tzinfo=timezone.utc).timestamp())
    time_dict['ninety_epoch'] = ninety_epoch
    august_epoch = int(datetime.datetime(2018, 8, 1).replace(tzinfo=timezone.utc).timestamp())
    time_dict['august_epoch'] = august_epoch
    january_epoch = int(datetime.datetime(2018, 1, 1).replace(tzinfo=timezone.utc).timestamp())
    time_dict['january_epoch'] = january_epoch

    for key in time_dict:
        fee_asset_dict = {}
        for fee_asset in ssc.ni.mongo_db['fees'].aggregate([
            {
                '$match': {
                    '$and': [
                        {'fee_amount': {'$ne': None}},
                        {'block_time': {'$gte': time_dict[key], '$lte': now_epoch}}
                    ]
                }
            }, {
                '$group': {
                    '_id': {'fee_asset_name': '$fee_asset_name'},
                    'total_fee_count': {
                        '$sum': 1
                    }
                }
            }
        ]):
            fee_asset_dict[fee_asset['_id']['fee_asset_name']] = fee_asset['total_fee_count']

        fees_dict[key] = fee_asset_dict

    return str(json.dumps(fees_dict))


@app.route('/switcheo/fee/amount/graph')
@cross_origin()
def switcheo_fee_amount_graph():
    return get_switcheo_fee_amount_graph()


def get_switcheo_fee_amount_graph():
    fees_dict = {}
    fees_v3_dict = {}

    for fee_asset_name in ssc.ni.mongo_db['fees'].distinct("fee_asset_name"):
        fees_dict[fee_asset_name] = []

    for fee_asset_name in ssc.ni.mongo_db['fees'].distinct("taker_fee_asset_name"):
        fees_dict[fee_asset_name] = []
        fees_v3_dict[fee_asset_name] = []

    for fee_asset in ssc.ni.mongo_db['fees'].aggregate([
        {
            '$match': {
                '$and': [
                    {'contract_hash_version': 'V2'},
                    {'fee_amount': {'$ne': None}},
                ]
            }
        }, {
            '$group': {
                '_id': {
                    'fee_asset_name': '$fee_asset_name',
                    'block_date': '$block_date'
                },
                'total_fee_amount': {
                    '$sum': '$fee_amount'
                }
            }
        }
    ]):
        fee_asset_dict = {
            'block_date': fee_asset['_id']['block_date'],
            'fee_amount': fee_asset['total_fee_amount'] / 100000000
        }
        fees_dict[fee_asset['_id']['fee_asset_name']].append(fee_asset_dict)

    for fee_asset in ssc.ni.mongo_db['fees'].aggregate([
        {
            '$match': {
                '$and': [
                    {'contract_hash_version': 'V3'},
                    {'taker_fee_burn_amount': {'$ne': None}},
                ]
            }
        }, {
            '$group': {
                '_id': {
                    'taker_fee_asset_name': '$taker_fee_asset_name',
                    'block_date': '$block_date'
                },
                'total_fee_amount': {
                    '$sum': '$taker_fee_burn_amount'
                }
            }
        }
    ]):
        fee_asset_dict = {
            'block_date': fee_asset['_id']['block_date'],
            'fee_amount': fee_asset['total_fee_amount'] / 100000000
        }
        fees_v3_dict[fee_asset['_id']['taker_fee_asset_name']].append(fee_asset_dict)

    for asset in fees_v3_dict:
        for block_date in fees_v3_dict[asset]:
            date_check = block_date['block_date']
            fee_for_date = block_date['fee_amount']
            i = 0
            date_match = False
            date_match_location = 0
            for fees_date in fees_dict[asset]:
                check_date = fees_date['block_date']
                if date_check == check_date:
                    date_match = True
                    date_match_location = i
                i += 1
            if date_match:
                fees_dict[asset][date_match_location]['fee_amount'] = fees_dict[asset][date_match_location]['fee_amount'] + fee_for_date
            else:
                fee_asset_dict = {
                    'block_date': date_check,
                    'fee_amount': fee_for_date
                }
                fees_dict[asset].append(fee_asset_dict)

    fee_asset_dict = {
        'block_date': '2018-07-24',
        'fee_amount': 646747
    }
    fees_dict['SWTH'].append(fee_asset_dict)

    fee_asset_dict = {
        'block_date': '2019-01-01',
        'fee_amount': 161052
    }
    fees_dict['SWTH'].append(fee_asset_dict)

    fee_asset_dict = {
        'block_date': '2019-04-01',
        'fee_amount': 293815
    }
    fees_dict['SWTH'].append(fee_asset_dict)

    fee_asset_dict = {
        'block_date': '2019-07-01',
        'fee_amount': 2184273
    }
    fees_dict['SWTH'].append(fee_asset_dict)

    for key in fees_dict.keys():
        fees_dict[key] = sorted(fees_dict[key], key=lambda coin: coin['block_date'])
        # if key is not None:
        #     fees_dict[key].sort(key=lambda coin: coin['block_date'])

    return str(json.dumps(fees_dict))


@app.route('/switcheo/addresses/fees')
@cross_origin()
def switcheo_addresses_fees():
    return get_switcheo_addresses_fees()


def get_switcheo_addresses_fees():
    return str(json.dumps(sort_dicts(collection='addresses',
                                     key_name='fees_paid',
                                     sort_key='fee_amount')))


@app.route('/switcheo/addresses/takes')
@cross_origin()
def switcheo_addresses_takes():
    return get_switcheo_addresses_takes()


def get_switcheo_addresses_takes():
    return str(json.dumps(sort_dicts(collection='addresses',
                                     key_name='takes',
                                     sort_key='trades',
                                     exclude_keys=['wants', 'offers'])))


@app.route('/switcheo/addresses/makes')
@cross_origin()
def switcheo_addresses_makes():
    return get_switcheo_addresses_makes()


def get_switcheo_addresses_makes():
    return str(json.dumps(sort_dicts(collection='addresses',
                                     key_name='makes',
                                     sort_key='trades',
                                     exclude_keys=['wants', 'offers'])))

@app.route('/switcheo/addresses/trades/count')
@cross_origin()
def switcheo_addresses_trades_count():
    return get_switcheo_addresses_trades_count()


def get_switcheo_addresses_trades_count():
    return str(json.dumps(sort_dicts(collection='addresses',
                                     key_name='trade_count',
                                     sort_key='trades')))


@app.route('/switcheo/addresses/trades/amount')
@cross_origin()
def switcheo_addresses_trades_amount():
    return get_switcheo_addresses_trades_amount()


def get_switcheo_addresses_trades_amount():
    return str(json.dumps(sort_dicts(collection='addresses',
                                     key_name='total_amount_traded',
                                     sort_key='trade_amount')))


@app.route('/switcheo/offers/open')
@cross_origin()
def switcheo_offers_open():
    return get_switcheo_offers_open()


def get_switcheo_offers_open():
    offer_list = []
    for offer in ssc.ni.mongo_db['offer_hash'].find({'status': 'open'}):
        if offer['_id'] is not None:
            trade_pair = offer['offer_asset_name'] + "_" + offer['want_asset_name']
            if trade_pair not in ssc.neo_trade_pair_list:
                trade_pair = offer['want_asset_name'] + "_" + offer['offer_asset_name']
                if trade_pair not in ssc.neo_trade_pair_list:
                    exit("Incorrect trade pair - " + trade_pair)
            offer_dict = {
                'address': offer['maker_address'],
                'amount_filled': offer['amount_filled'],
                'trade_pair': trade_pair,
                'offer_amount': offer['offer_amount_fixed8'],
                'offer_asset_name': offer['offer_asset_name'],
                'want_amount': offer['want_amount_fixed8'],
                'want_asset_name': offer['want_asset_name']
            }
            offer_list.append(offer_dict)
    return str(json.dumps(offer_list))


@app.route('/switcheo/richlist')
@cross_origin()
def switcheo_richlist():
    return get_switcheo_richlist()


def get_switcheo_richlist():
    richlist_dict = {}
    addresses = ssc.ni.mongo_db['addresses'].find()

    for address in addresses:
        if 'rich_list' in address:
            asset_dict = {
                'address': address['_id'],
                'smart_contract': address['rich_list']['smart_contract'],
                'on_chain': address['rich_list']['on_chain'],
                'total': address['rich_list']['total']
            }
            if 'SWTH' not in richlist_dict:
                richlist_dict['SWTH'] = []
            richlist_dict['SWTH'].append(asset_dict)

    for asset in richlist_dict.keys():
        richlist_dict[asset] = sorted(richlist_dict[asset], key=lambda coin: coin['total'], reverse=True)

    return str(json.dumps(richlist_dict))


@app.route('/<path:path>')
@cross_origin()
def static_proxy(path):
    """ static folder serve """
    return send_from_directory('dist', 'index.html')


if __name__ == "__main__":
    app.run()
