from flask import Blueprint, render_template, request, flash, jsonify
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from .models import User, Ticker
from . import db
import json
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.layouts import row
from bokeh.models import Range1d, LinearAxis, Span, CustomJS, ColumnDataSource, NumeralTickFormatter
from bokeh.layouts import gridplot, row
import pandas_ta as pta

views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == "POST":
        ticker = request.form.get('ticker').upper()
        amount = request.form.get('amount')
        if amount == "":
            amount = 0
        if not isValidAsset(ticker):
            flash('Ticker is invalid', category='error')
        else:
            unique = True
            for asset in current_user.tickers:
                if ticker == asset.data:
                    unique = False
                    break
            if unique:
                new_ticker = Ticker(data=ticker, amount_of_supply=amount, user_id=current_user.id)
                db.session.add(new_ticker)
                db.session.commit()
                flash("Ticker added", category='success')
            else:
                flash("Ticker has already been added", category='error')
    return render_template("portfolio.html", user=current_user)


def isValidAsset(ticker):
    try:
        data = yf.Ticker(ticker).history(period='1mo')
        price = data.iloc[-1].Close
        return True
    except (IndexError, KeyError, TypeError, ValueError, yf.shared.TickerError):
        return False


@views.route('/get_stock_data', methods=['POST'])
def get_stock_data():
    ticker = request.get_json()['ticker']
    data = yf.Ticker(ticker).history(period='1y')
    return jsonify({'currentPrice': data.iloc[-1].Close,
                    'openPrice': data.iloc[-1].Open})


@views.route('/delete-ticker', methods=['POST'])
def delete_note():
    ticker = json.loads(request.data)
    tickerId = ticker['tickerId']
    ticker = Ticker.query.get(tickerId)
    if ticker:
        if ticker.user_id == current_user.id:
            db.session.delete(ticker)
            db.session.commit()
    return jsonify({})


@views.route('/update_amount', methods=['POST'])
def update_value():
    item_id = request.form.get('id')
    new_amount = request.form.get('value')
    try:
        new_amount = float(new_amount)
    except (ValueError, TypeError):
        return jsonify({'success': False})
    if new_amount < 0:
        return jsonify({'success': False})

    item = Ticker.query.get(item_id)
    if item:
        item.amount_of_supply = new_amount
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})


@views.route('/ta', methods=['GET', 'POST'])
def ta():
    if request.method == "POST":
        ticker = request.form.get('ticker')
        indicators = request.form.getlist('checkbox')
        start = request.form.get('start')
        end = request.form.get('end')
        colors = request.form.getlist('color')

        # if user does not select any asset
        if ticker == "None":
            flash('You must select an asset! In the event there are no options present, add some assets to your portfolio on the Portfolio page!', category='error')
            script = ''
            div = ''
            return render_template('ta.html', user=current_user, script=script, div=div)

        # timeframe for downloading and displaying data
        final_date = datetime.today().strftime('%Y-%m-%d')
        final_date_parsed = final_date.split('-')
        final_date_padding = datetime(int(final_date_parsed[0]), int(final_date_parsed[1]), int(final_date_parsed[2])) + timedelta(days=10)
        earliest_date = 0

        df = yf.download(ticker, earliest_date, final_date)
        df = df[df['Volume'] != 0]

        source = ColumnDataSource(df)

        # displaying daily chart
        gain = df.Close > df.Open
        loss = df.Open > df.Close
        width = 12 * 60 * 60 * 1000

        p = figure(x_axis_type="datetime", tools="pan,wheel_zoom,box_zoom,reset,save", title=f"{ticker} Daily Chart", outline_line_color='#000000', sizing_mode='stretch_width', width=1000, height=500)
        p.grid.grid_line_alpha = 0.25

        low, high = df[['Open', 'Adj Close']].min().min(), df[['Open', 'Adj Close']].max().max()
        diff = high - low
        p.y_range = Range1d(low - 0.1 * diff, high + 0.1 * diff)
        p.y_range.bounds = (0, high + 0.1 * diff)
        p.yaxis.axis_label = 'Price'

        p.x_range = Range1d(start=pd.Timestamp(start), end=pd.Timestamp(end))
        p.x_range.bounds = (df.index[0], df.index[-1])
        p.x_range.bounds = (df.index[0], final_date_padding)

        p.segment(df.index, df.High, df.index, df.Low, color="black")
        p.vbar(df.index[gain], width, df.Open[gain], df['Adj Close'][gain], fill_color="#00ff00", line_color="#00ff00")
        p.vbar(df.index[loss], width, df.Open[loss], df['Adj Close'][loss], fill_color="#ff0000", line_color="#ff0000")

        p.extra_y_ranges.update({'two': Range1d(0, 2 * df.Volume.max())})
        p.extra_y_ranges['two'].bounds = (0, 2 * df.Volume.max())
        p.add_layout(LinearAxis(y_range_name='two', axis_label='Volume'), 'right')
        p.vbar(df.index, width, df.Volume, [0] * df.shape[0], alpha=0.5, level='underlay', legend_label='Volume', y_range_name="two")

        p.yaxis[0].formatter = NumeralTickFormatter(format="$ 0,0")
        p.yaxis[1].formatter = NumeralTickFormatter(format="($ 0.00 a)")

        # displaying indicators
        for indicator in indicators:
            if indicator == "5 Day SMA":
                df['SMA5'] = df['Adj Close'].rolling(5).mean()
                p.line(df.index, df.SMA5, color=colors[5], legend_label="5 Day SMA")
            elif indicator == "10 Day SMA":
                df['SMA10'] = df['Adj Close'].rolling(10).mean()
                p.line(df.index, df.SMA10, color=colors[4], legend_label="10 Day SMA")
            elif indicator == "20 Day SMA":
                df['SMA20'] = df['Adj Close'].rolling(20).mean()
                p.line(df.index, df.SMA20, color=colors[3], legend_label="20 Day SMA")
            if indicator == "50 Day SMA":
                df['SMA50'] = df['Adj Close'].rolling(50).mean()
                p.line(df.index, df.SMA50, color=colors[2], legend_label="50 Day SMA")
            elif indicator == "100 Day SMA":
                df['SMA100'] = df['Adj Close'].rolling(100).mean()
                p.line(df.index, df.SMA100, color=colors[1], legend_label="100 Day SMA")
            elif indicator == "200 Day SMA":
                df['SMA200'] = df['Adj Close'].rolling(200).mean()
                p.line(df.index, df.SMA200, color=colors[0], legend_label="200 Day SMA")
            elif indicator == "5 Day EMA":
                df['EMA5'] = df['Adj Close'].ewm(span=5, adjust=False).mean()
                p.line(df.index, df.EMA5, color=colors[11], legend_label="5 Day EMA")
            elif indicator == "10 Day EMA":
                df['EMA10'] = df['Adj Close'].ewm(span=10, adjust=False).mean()
                p.line(df.index, df.EMA10, color=colors[10], legend_label="10 Day EMA")
            elif indicator == "20 Day EMA":
                df['EMA20'] = df['Adj Close'].ewm(span=20, adjust=False).mean()
                p.line(df.index, df.EMA20, color=colors[9], legend_label="20 Day EMA")
            elif indicator == "50 Day EMA":
                df['EMA50'] = df['Adj Close'].ewm(span=50, adjust=False).mean()
                p.line(df.index, df.EMA50, color=colors[8], legend_label="50 Day EMA")
            elif indicator == "100 Day EMA":
                df['EMA100'] = df['Adj Close'].ewm(span=100, adjust=False).mean()
                p.line(df.index, df.EMA100, color=colors[7], legend_label="100 Day EMA")
            elif indicator == "200 Day EMA":
                df['EMA200'] = df['Adj Close'].ewm(span=200, adjust=False).mean()
                p.line(df.index, df.EMA200, color=colors[6], legend_label="200 Day EMA")
            elif indicator == "5 Day VWMA":
                vwma = pta.vwma(df['Adj Close'], df['Volume'], 5)
                p.line(df.index, vwma, color=colors[17], legend_label="5 Day VWMA")
            elif indicator == "10 Day VWMA":
                vwma = pta.vwma(df['Adj Close'], df['Volume'], 10)
                p.line(df.index, vwma, color=colors[16], legend_label="10 Day VWMA")
            elif indicator == "20 Day VWMA":
                vwma = pta.vwma(df['Adj Close'], df['Volume'], 20)
                p.line(df.index, vwma, color=colors[15], legend_label="20 Day VWMA")
            elif indicator == "50 Day VWMA":
                vwma = pta.vwma(df['Adj Close'], df['Volume'], 50)
                p.line(df.index, vwma, color=colors[14], legend_label="50 Day VWMA")
            elif indicator == "100 Day VWMA":
                vwma = pta.vwma(df['Adj Close'], df['Volume'], 100)
                p.line(df.index, vwma, color=colors[13], legend_label="100 Day VWMA")
            elif indicator == "200 Day VWMA":
                vwma = pta.vwma(df['Adj Close'], df['Volume'], 200)
                p.line(df.index, vwma, color=colors[12], legend_label="200 Day VWMA")
            elif indicator == "RSI":
                combined = pd.DataFrame()
                combined['Adj Close'] = df['Adj Close']
                combined['RSI'] = pta.rsi(close=df["Adj Close"])

                source_rsi = ColumnDataSource(combined)

                p_rsi = figure(x_axis_type="datetime", tools="pan, wheel_zoom, box_zoom, reset, save", title="RSI", x_range=p.x_range, sizing_mode='stretch_width', width=250, height=250)
                p_rsi.y_range.bounds = (0, 100)
                p_rsi.line(combined.index, combined["RSI"], color="gray")
                line0 = Span(location=0, dimension='width', line_color='#ff0000', line_width=1)
                line10 = Span(location=10, dimension='width', line_color='#ffaa00', line_width=1)
                line20 = Span(location=20, dimension='width', line_color='#00ff00', line_width=1)
                line30 = Span(location=30, dimension='width', line_color='#cccccc', line_width=1)
                line70 = Span(location=70, dimension='width', line_color='#cccccc', line_width=1)
                line80 = Span(location=80, dimension='width', line_color='#00ff00', line_width=1)
                line90 = Span(location=90, dimension='width', line_color='#ffaa00', line_width=1)
                line100 = Span(location=100, dimension='width', line_color='#ff0000', line_width=1)
                p_rsi.renderers.extend([line0, line10, line20, line30, line70, line80, line90, line100])
            elif indicator == "ADX":
                adx = pta.adx(high=df['High'], low=df['Low'], close=df['Adj Close'])

                p_adx = figure(x_axis_type="datetime", tools="pan, wheel_zoom, box_zoom, reset, save", title="ADX", x_range=p.x_range, sizing_mode='stretch_width', width=250, height=250)
                p_adx.y_range.bounds = (0, 100)
                p_adx.line(df.index, adx['ADX_14'], color="blue", legend_label="ADX")
                p_adx.line(df.index, adx['DMP_14'], color="red", legend_label="+DMI")
                p_adx.line(df.index, adx['DMN_14'], color="green", legend_label="-DMI")

                p_adx.legend.location = "top_left"
                source_adx = ColumnDataSource(adx)
            elif indicator == "MACD":
                macd = df.copy()
                macd['EMA12'] = df['Adj Close'].ewm(span=12, adjust=False).mean()
                macd['EMA26'] = df['Adj Close'].ewm(span=26, adjust=False).mean()
                macd['MACD'] = macd['EMA12'] - macd['EMA26']
                macd['Signal'] = macd['MACD'].ewm(span=9, adjust=False).mean()
                macd['Histogram'] = macd['MACD'] - macd['Signal']

                positive_hist = macd['Histogram'].copy()
                negative_hist = macd['Histogram'].copy()
                positive_hist[positive_hist < 0] = 0
                negative_hist[negative_hist > 0] = 0

                p_macd = figure(x_axis_type="datetime", tools="pan, wheel_zoom, box_zoom, reset, save", title="MACD", x_range=p.x_range, sizing_mode='stretch_width', width=250, height=250)
                p_macd.line(df.index, macd['MACD'], color='blue', legend_label="MACD Line")
                p_macd.line(df.index, macd['Signal'], color="#8B8000", legend_label="Signal Line")
                p_macd.vbar(df.index, width, positive_hist, [0] * df.shape[0], alpha=0.5, level='underlay', color="green")
                p_macd.vbar(df.index, width, negative_hist, [0] * df.shape[0], alpha=0.5, level='underlay', color="red")

                p_macd.legend.location = "top_left"
                source_macd = ColumnDataSource(macd)
            elif indicator == "CCI":
                cci = df.copy()
                cci['CCI'] = pta.cci(high=df['High'], low=df['Low'], close=df['Adj Close'], length=20)

                p_cci = figure(x_axis_type="datetime", tools="pan, wheel_zoom, box_zoom, reset, save", title="CCI", x_range=p.x_range, sizing_mode='stretch_width', width=250, height=250)
                p_cci.line(df.index, cci['CCI'], color='gray')

                source_cci = ColumnDataSource(cci)
                pass

        p.legend.location = "top_left"
        p.legend.click_policy = "hide"

        wheel_zoom = p.toolbar.tools[1]
        wheel_zoom.zoom_together = 'none'
        p.toolbar.active_scroll = wheel_zoom

        vline = Span(location=0, dimension='height', line_color='black', line_width=1, line_dash='dashed')
        p.add_layout(vline)

        # adding vertical moving line to other plots, and combining all plots into a gridplot
        if ("RSI" in indicators) and ("MACD" in indicators) and ("ADX" in indicators) and ("CCI" in indicators):
            p_rsi.add_layout(vline)
            p_adx.add_layout(vline)
            p_macd.add_layout(vline)
            p_cci.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_rsi=p_rsi, p_macd=p_macd, p_adx=p_adx, p_cci=p_cci, vline=vline, source=source, source_rsi=source_rsi, source_macd=source_macd, source_adx=source_adx, source_cci=source_cci), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;

                const data = source.data;
                const data_rsi = source_rsi.data;
                const data_macd = source_macd.data;
                const data_adx = source_adx.data;
                const data_cci = source_cci.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const rsi_value = data_rsi['RSI'][closest_index].toFixed(2);
                    const macd_value = data_macd['MACD'][closest_index].toFixed(2);
                    const signal_value = data_macd['Signal'][closest_index].toFixed(2);
                    const hist_value = data_macd['Histogram'][closest_index].toFixed(2);
                    const adx_value = data_adx['ADX_14'][closest_index].toFixed(2);
                    const dmp_value = data_adx['DMP_14'][closest_index].toFixed(2);
                    const dmn_value = data_adx['DMN_14'][closest_index].toFixed(2);
                    const cci_value = data_cci['CCI'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleDateString("en-GB")}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span style="font-size: 15px;"><strong>RSI:</strong> ${rsi_value}</span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD:</strong> ${macd_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>Signal Line:</strong> ${signal_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD Histogram:</strong> ${hist_value}</span>
                        </span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>ADX:</strong> ${adx_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>+DMI:</strong> ${dmp_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>-DMI:</strong> ${dmn_value}</span>
                        </span>
                        <span style="font-size: 15px;"><strong>CCI:</strong> ${cci_value}</span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'flex';

                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_rsi.js_on_event('mousemove', js_callback)
            p_macd.js_on_event('mousemove', js_callback)
            p_adx.js_on_event('mousemove', js_callback)
            p_cci.js_on_event('mousemove', js_callback)

            oscillators_row = row(p_rsi, p_macd, p_adx, p_cci)
            layout = gridplot([[p], [oscillators_row]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("RSI" in indicators) and ("MACD" in indicators) and ("ADX" in indicators):
            p_rsi.add_layout(vline)
            p_adx.add_layout(vline)
            p_macd.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_rsi=p_rsi, p_macd=p_macd, p_adx=p_adx, vline=vline, source=source, source_rsi=source_rsi, source_macd=source_macd, source_adx=source_adx), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_rsi = source_rsi.data;
                const data_macd = source_macd.data;
                const data_adx = source_adx.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const rsi_value = data_rsi['RSI'][closest_index].toFixed(2);
                    const macd_value = data_macd['MACD'][closest_index].toFixed(2);
                    const signal_value = data_macd['Signal'][closest_index].toFixed(2);
                    const hist_value = data_macd['Histogram'][closest_index].toFixed(2);
                    const adx_value = data_adx['ADX_14'][closest_index].toFixed(2);
                    const dmp_value = data_adx['DMP_14'][closest_index].toFixed(2);
                    const dmn_value = data_adx['DMN_14'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span style="font-size: 15px;"><strong>RSI:</strong> ${rsi_value}</span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD:</strong> ${macd_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>Signal Line:</strong> ${signal_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD Histogram:</strong> ${hist_value}</span>
                        </span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>ADX:</strong> ${adx_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>+DMI:</strong> ${dmp_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>-DMI:</strong> ${dmn_value}</span>
                        </span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';


                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_rsi.js_on_event('mousemove', js_callback)
            p_macd.js_on_event('mousemove', js_callback)
            p_adx.js_on_event('mousemove', js_callback)

            oscillators_row = row(p_rsi, p_macd, p_adx)
            layout = gridplot([[p], [oscillators_row]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("RSI" in indicators) and ("MACD" in indicators) and ("CCI" in indicators):
            p_rsi.add_layout(vline)
            p_macd.add_layout(vline)
            p_cci.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_rsi=p_rsi, p_macd=p_macd, p_cci=p_cci, vline=vline, source=source, source_rsi=source_rsi, source_macd=source_macd, source_cci=source_cci), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_rsi = source_rsi.data;
                const data_macd = source_macd.data;
                const data_cci = source_cci.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const rsi_value = data_rsi['RSI'][closest_index].toFixed(2);
                    const macd_value = data_macd['MACD'][closest_index].toFixed(2);
                    const signal_value = data_macd['Signal'][closest_index].toFixed(2);
                    const hist_value = data_macd['Histogram'][closest_index].toFixed(2);
                    const cci_value = data_cci['CCI'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span style="font-size: 15px;"><strong>RSI:</strong> ${rsi_value}</span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD:</strong> ${macd_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>Signal Line:</strong> ${signal_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD Histogram:</strong> ${hist_value}</span>
                        </span>
                        <span style="font-size: 15px;"><strong>CCI:</strong> ${cci_value}</span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';

                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_rsi.js_on_event('mousemove', js_callback)
            p_macd.js_on_event('mousemove', js_callback)
            p_cci.js_on_event('mousemove', js_callback)

            oscillators_row = row(p_rsi, p_macd, p_cci)
            layout = gridplot([[p], [oscillators_row]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("RSI" in indicators) and ("ADX" in indicators) and ("CCI" in indicators):
            p_rsi.add_layout(vline)
            p_adx.add_layout(vline)
            p_cci.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_rsi=p_rsi, p_adx=p_adx, p_cci=p_cci, vline=vline, source=source, source_rsi=source_rsi, source_adx=source_adx, source_cci=source_cci), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_rsi = source_rsi.data;
                const data_adx = source_adx.data;
                const data_cci = source_cci.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const rsi_value = data_rsi['RSI'][closest_index].toFixed(2);
                    const adx_value = data_adx['ADX_14'][closest_index].toFixed(2);
                    const dmp_value = data_adx['DMP_14'][closest_index].toFixed(2);
                    const dmn_value = data_adx['DMN_14'][closest_index].toFixed(2);
                    const cci_value = data_cci['CCI'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span style="font-size: 15px;"><strong>RSI:</strong> ${rsi_value}</span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>ADX:</strong> ${adx_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>+DMI:</strong> ${dmp_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>-DMI:</strong> ${dmn_value}</span>
                        </span>
                        <span style="font-size: 15px;"><strong>CCI:</strong> ${cci_value}</span>
                    </div>`;


                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';


                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_rsi.js_on_event('mousemove', js_callback)
            p_adx.js_on_event('mousemove', js_callback)
            p_cci.js_on_event('mousemove', js_callback)

            oscillators_row = row(p_rsi, p_adx, p_cci)
            layout = gridplot([[p], [oscillators_row]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("MACD" in indicators) and ("ADX" in indicators) and ("CCI" in indicators):
            p_adx.add_layout(vline)
            p_macd.add_layout(vline)
            p_cci.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_macd=p_macd, p_adx=p_adx, p_cci=p_cci, vline=vline, source=source, source_macd=source_macd, source_adx=source_adx, source_cci=source_cci), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_macd = source_macd.data;
                const data_adx = source_adx.data;
                const data_cci = source_cci.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const macd_value = data_macd['MACD'][closest_index].toFixed(2);
                    const signal_value = data_macd['Signal'][closest_index].toFixed(2);
                    const hist_value = data_macd['Histogram'][closest_index].toFixed(2);
                    const adx_value = data_adx['ADX_14'][closest_index].toFixed(2);
                    const dmp_value = data_adx['DMP_14'][closest_index].toFixed(2);
                    const dmn_value = data_adx['DMN_14'][closest_index].toFixed(2);
                    const cci_value = data_cci['CCI'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD:</strong> ${macd_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>Signal Line:</strong> ${signal_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD Histogram:</strong> ${hist_value}</span>
                        </span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>ADX:</strong> ${adx_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>+DMI:</strong> ${dmp_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>-DMI:</strong> ${dmn_value}</span>
                        </span>
                        <span style="font-size: 15px;"><strong>CCI:</strong> ${cci_value}</span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';


                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_macd.js_on_event('mousemove', js_callback)
            p_adx.js_on_event('mousemove', js_callback)
            p_cci.js_on_event('mousemove', js_callback)

            oscillators_row = row(p_macd, p_adx, p_cci)
            layout = gridplot([[p], [oscillators_row]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("RSI" in indicators) and ("MACD" in indicators):
            p_rsi.add_layout(vline)
            p_macd.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_rsi=p_rsi, p_macd=p_macd, vline=vline, source=source, source_rsi=source_rsi, source_macd=source_macd), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_rsi = source_rsi.data;
                const data_macd = source_macd.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const rsi_value = data_rsi['RSI'][closest_index].toFixed(2);
                    const macd_value = data_macd['MACD'][closest_index].toFixed(2);
                    const signal_value = data_macd['Signal'][closest_index].toFixed(2);
                    const hist_value = data_macd['Histogram'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span style="font-size: 15px;"><strong>RSI:</strong> ${rsi_value}</span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD:</strong> ${macd_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>Signal Line:</strong> ${signal_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD Histogram:</strong> ${hist_value}</span>
                        </span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';


                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_rsi.js_on_event('mousemove', js_callback)
            p_macd.js_on_event('mousemove', js_callback)

            oscillators_row = row(p_rsi, p_macd)
            layout = gridplot([[p], [oscillators_row]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("RSI" in indicators) and ("ADX" in indicators):
            p_rsi.add_layout(vline)
            p_adx.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_rsi=p_rsi, p_adx=p_adx, vline=vline, source=source, source_rsi=source_rsi, source_adx=source_adx), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_rsi = source_rsi.data;
                const data_adx = source_adx.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const rsi_value = data_rsi['RSI'][closest_index].toFixed(2);
                    const adx_value = data_adx['ADX_14'][closest_index].toFixed(2);
                    const dmp_value = data_adx['DMP_14'][closest_index].toFixed(2);
                    const dmn_value = data_adx['DMN_14'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span style="font-size: 15px;"><strong>RSI:</strong> ${rsi_value}</span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>ADX:</strong> ${adx_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>+DMI:</strong> ${dmp_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>-DMI:</strong> ${dmn_value}</span>
                        </span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';

                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_rsi.js_on_event('mousemove', js_callback)
            p_adx.js_on_event('mousemove', js_callback)

            oscillators_row = row(p_rsi, p_adx)
            layout = gridplot([[p], [oscillators_row]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("RSI" in indicators) and ("CCI" in indicators):
            p_rsi.add_layout(vline)
            p_cci.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_rsi=p_rsi, p_cci=p_cci, vline=vline, source=source, source_rsi=source_rsi, source_cci=source_cci), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_rsi = source_rsi.data;
                const data_cci = source_cci.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const rsi_value = data_rsi['RSI'][closest_index].toFixed(2);
                    const cci_value = data_cci['CCI'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span style="font-size: 15px;"><strong>RSI:</strong> ${rsi_value}</span>
                        <span style="font-size: 15px;"><strong>CCI:</strong> ${cci_value}</span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';

                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_rsi.js_on_event('mousemove', js_callback)
            p_cci.js_on_event('mousemove', js_callback)

            oscillators_row = row(p_rsi, p_cci)
            layout = gridplot([[p], [oscillators_row]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("MACD" in indicators) and ("ADX" in indicators):
            p_adx.add_layout(vline)
            p_macd.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_macd=p_macd, p_adx=p_adx, vline=vline, source=source, source_macd=source_macd, source_adx=source_adx), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_macd = source_macd.data;
                const data_adx = source_adx.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const macd_value = data_macd['MACD'][closest_index].toFixed(2);
                    const signal_value = data_macd['Signal'][closest_index].toFixed(2);
                    const hist_value = data_macd['Histogram'][closest_index].toFixed(2);
                    const adx_value = data_adx['ADX_14'][closest_index].toFixed(2);
                    const dmp_value = data_adx['DMP_14'][closest_index].toFixed(2);
                    const dmn_value = data_adx['DMN_14'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD:</strong> ${macd_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>Signal Line:</strong> ${signal_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD Histogram:</strong> ${hist_value}</span>
                        </span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>ADX:</strong> ${adx_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>+DMI:</strong> ${dmp_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>-DMI:</strong> ${dmn_value}</span>
                        </span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';

                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_macd.js_on_event('mousemove', js_callback)
            p_adx.js_on_event('mousemove', js_callback)

            oscillators_row = row(p_macd, p_adx)
            layout = gridplot([[p], [oscillators_row]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("MACD" in indicators) and ("CCI" in indicators):
            p_macd.add_layout(vline)
            p_cci.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_macd=p_macd, p_cci=p_cci, vline=vline, source=source, source_macd=source_macd, source_cci=source_cci), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_macd = source_macd.data;
                const data_cci = source_cci.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const macd_value = data_macd['MACD'][closest_index].toFixed(2);
                    const signal_value = data_macd['Signal'][closest_index].toFixed(2);
                    const hist_value = data_macd['Histogram'][closest_index].toFixed(2);
                    const cci_value = data_cci['CCI'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD:</strong> ${macd_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>Signal Line:</strong> ${signal_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD Histogram:</strong> ${hist_value}</span>
                        </span>
                        <span style="font-size: 15px;"><strong>CCI:</strong> ${cci_value}</span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';

                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_macd.js_on_event('mousemove', js_callback)
            p_cci.js_on_event('mousemove', js_callback)

            oscillators_row = row(p_macd, p_cci)
            layout = gridplot([[p], [oscillators_row]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("ADX" in indicators) and ("CCI" in indicators):
            p_adx.add_layout(vline)
            p_cci.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_adx=p_adx, p_cci=p_cci, vline=vline, source=source, source_adx=source_adx, source_cci=source_cci), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_adx = source_adx.data;
                const data_cci = source_cci.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const adx_value = data_adx['ADX_14'][closest_index].toFixed(2);
                    const dmp_value = data_adx['DMP_14'][closest_index].toFixed(2);
                    const dmn_value = data_adx['DMN_14'][closest_index].toFixed(2);
                    const cci_value = data_cci['CCI'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>ADX:</strong> ${adx_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>+DMI:</strong> ${dmp_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>-DMI:</strong> ${dmn_value}</span>
                        </span>
                        <span style="font-size: 15px;"><strong>CCI:</strong> ${cci_value}</span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';

                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_adx.js_on_event('mousemove', js_callback)
            p_cci.js_on_event('mousemove', js_callback)

            oscillators_row = row(p_adx, p_cci)
            layout = gridplot([[p], [oscillators_row]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("CCI" in indicators):
            p_cci.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_cci=p_cci, vline=vline, source=source, source_cci=source_cci), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_cci = source_cci.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const cci_value = data_cci['CCI'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span style="font-size: 15px;"><strong>CCI:</strong> ${cci_value}</span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';

                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_cci.js_on_event('mousemove', js_callback)

            layout = gridplot([[p], [p_cci]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("RSI" in indicators):
            p_rsi.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_rsi=p_rsi, vline=vline, source=source, source_rsi=source_rsi), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_rsi = source_rsi.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const rsi_value = data_rsi['RSI'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span style="font-size: 15px;"><strong>RSI:</strong> ${rsi_value}</span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';

                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_rsi.js_on_event('mousemove', js_callback)

            layout = gridplot([[p], [p_rsi]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("MACD" in indicators):
            p_macd.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_macd=p_macd, vline=vline, source=source, source_macd=source_macd), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;

                const data = source.data;
                const data_macd = source_macd.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const macd_value = data_macd['MACD'][closest_index].toFixed(2);
                    const signal_value = data_macd['Signal'][closest_index].toFixed(2);
                    const hist_value = data_macd['Histogram'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD:</strong> ${macd_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>Signal Line:</strong> ${signal_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>MACD Histogram:</strong> ${hist_value}</span>
                        </span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';

                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_macd.js_on_event('mousemove', js_callback)

            layout = gridplot([[p], [p_macd]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        elif ("ADX" in indicators):
            p_adx.add_layout(vline)
            js_callback = CustomJS(args=dict(p=p, p_adx=p_adx, vline=vline, source=source, source_adx=source_adx), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;
                const data_adx = source_adx.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);
                    const adx_value = data_adx['ADX_14'][closest_index].toFixed(2);
                    const dmp_value = data_adx['DMP_14'][closest_index].toFixed(2);
                    const dmn_value = data_adx['DMN_14'][closest_index].toFixed(2);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                        <span>
                            <span style="font-size: 15px;" class="additional"><strong>ADX:</strong> ${adx_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>+DMI:</strong> ${dmp_value}</span>
                            <span style="font-size: 15px;" class="additional"><strong>-DMI:</strong> ${dmn_value}</span>
                        </span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'block';

                }
            """)

            p.js_on_event('mousemove', js_callback)
            p_adx.js_on_event('mousemove', js_callback)

            layout = gridplot([[p], [p_adx]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)

        else:
            js_callback = CustomJS(args=dict(p=p, vline=vline, source=source), code="""

                const x = cb_obj.x;
                const y = cb_obj.y;
                vline.location = x;


                const data = source.data;

                const date = new Date(x);
                const closest_index = data['Date'].findIndex(d => Math.abs(new Date(d) - date) < 86400000);

                if (closest_index >= 0) {
                    var close_price = data['Adj Close'][closest_index].toFixed(2);
                    var options = { style: 'currency', currency: 'USD' };
                    var formatter = new Intl.NumberFormat('en-US', options);
                    close_price = formatter.format(close_price);
                    var volume_value = data['Volume'][closest_index];
                    volume_value = formatter.format(volume_value);

                    const tooltip_p = `<div>
                        <span style="font-size: 15px;"><strong>Date:</strong> ${new Date(data['Date'][closest_index]).toLocaleString()}</span>
                        <span style="font-size: 15px;"><strong>Adj Close Price:</strong> ${close_price}</span>
                        <span style="font-size: 15px;"><strong>Volume:</strong> ${volume_value}</span>
                    </div>`;

                    document.getElementById('hover-tooltip-p').innerHTML = tooltip_p;
                    document.getElementById('hover-tooltip-p').style.display = 'flex';

                }
            """)

            p.js_on_event('mousemove', js_callback)

            layout = gridplot([[p]], sizing_mode='stretch_width')
            script, div = components(layout)
            return render_template('ta.html', user=current_user, script=script, div=div)
    else:
        script = ''
        div = ''
        return render_template('ta.html', user=current_user, script=script, div=div)
