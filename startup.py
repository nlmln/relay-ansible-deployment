#!/usr/bin/env python3
import RPi.GPIO as GPIO
from flask import Flask, render_template, jsonify
import threading
import time
TIMER_DURATION = 900  # Timer duration in seconds
IP_ADDRESS = '0.0.0.0'
PORT = 80
# GPIO setup
#Output pins for relays [5, 6, 13, 16, 19, 20, 21, 26]
OUTPUT_PINS = [5, 6, 13, 16]
#Input pins for activating timers [2, 3, 4, 17, 27, 22, 10, 9]
#ADD_INPUT_PINS = [0, 1, 12, 19]
ADD_INPUT_PINS = [2, 3, 4, 17]
PHYSICAL_BUTTON_PIN = 18  # De pin voor de fysieke knop
GPIO.setmode(GPIO.BCM)
# Initialize GPIO pins
for pin in OUTPUT_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)
for pin in ADD_INPUT_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# Initialiseer de fysieke knop
GPIO.setup(PHYSICAL_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
timers = {pin: 0 for pin in OUTPUT_PINS}
active = {pin: False for pin in OUTPUT_PINS}
app = Flask(__name__)
def control_output(pin):
    global timers
    while True:
        if active[pin]:
            time.sleep(1)
            if timers[pin] > 0:
                timers[pin] -= 1
                if timers[pin] == 0:
                    GPIO.output(pin, GPIO.HIGH)
                    active[pin] = False
        else:
            time.sleep(1)
def button_press(pin_index):
    output_pin = OUTPUT_PINS[pin_index]
    global timers, active
    timers[output_pin] += TIMER_DURATION
    active[output_pin] = True
    GPIO.output(output_pin, GPIO.LOW)
def button_subtract(pin_index):
    output_pin = OUTPUT_PINS[pin_index]
    global timers
    timers[output_pin] = max(0, timers[output_pin] - TIMER_DURATION)
def monitor_inputs():
    while True:
        for i, pin in enumerate(ADD_INPUT_PINS):
            if GPIO.input(pin) == GPIO.LOW:
                button_press(i)
                time.sleep(0.5)  # debounce
        if GPIO.input(PHYSICAL_BUTTON_PIN) == GPIO.LOW:
            for pin in OUTPUT_PINS:
                timers[pin] = 0
                active[pin] = False
                GPIO.output(pin, GPIO.HIGH)
            time.sleep(0.5)  # debounce
@app.route('/')
def index():
    return render_template('bowling.html', timers=timers, active=active)
@app.route('/timers')
def display():
    # Nieuwe route voor het tonen van de timers op een aparte pagina
    return render_template('timers.html', timers=timers, active=active)
    
@app.route('/activate/<int:pin>', methods=['POST'])
def activate(pin):
    global timers
    if pin in timers:
        timers[pin] += TIMER_DURATION
        active[pin] = True
        GPIO.output(pin, GPIO.LOW)
        return jsonify(success=True)
    return jsonify(success=False)
@app.route('/subtract/<int:pin>', methods=['POST'])
def subtract(pin):
    global timers, active
    if pin in timers:
        timers[pin] = max(0, timers[pin] - TIMER_DURATION)
        if timers[pin] == 0:
            GPIO.output(pin, GPIO.HIGH)
            active[pin] = False
        return jsonify(success=True)
    return jsonify(success=False)
@app.route('/cancel/<int:pin>', methods=['POST'])
def cancel(pin):
    global timers, active
    if pin in timers:
        timers[pin] = 0
        active[pin] = False
        GPIO.output(pin, GPIO.HIGH)
        return jsonify(success=True)
    return jsonify(success=False)
@app.route('/reset', methods=['POST'])
def reset():
    global timers, active
    for pin in OUTPUT_PINS:
        timers[pin] = 0
        active[pin] = False
        GPIO.output(pin, GPIO.HIGH)
    return jsonify(success=True)
@app.route('/status')
def status():
    formatted_timers = {pin: f"{timers[pin] // 60}:{timers[pin] % 60:02}" for pin in timers}
    return jsonify(timers=formatted_timers, active=active)
def start_threads():
    for pin in OUTPUT_PINS:
        threading.Thread(target=control_output, args=(pin,), daemon=True).start()
    threading.Thread(target=monitor_inputs, daemon=True).start()
if __name__ == '__main__':
    start_threads()
    app.run(host=IP_ADDRESS, port=PORT, threaded=True)
