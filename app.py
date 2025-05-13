from flask import Flask, request, jsonify
import subprocess
import tempfile
import os
import sys

app = Flask(__name__)

# recorded = ['test1', 'test2']


@app.route('/', methods=['GET'])
def index():
    try:
        expected_bars = int(request.args.get('expected_bars', '') or 5)
    except ValueError:
        expected_bars = 5

    # return '<h1>Hello, world!</h1>'
    # return send_file('index.html')
    return '''
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LabelLifter - the barcode scanner (for smarty phones)</title>
  <style>
    body { font-family: sans-serif; padding: 1em; }
    h1, h2, h3, h4 { margin: 0; padding: 2px; }
    ul, p { font-size: 14px; }
    button, input { font-size: 12px; }
    table, th, td {
      border: 1px solid; border-collapse: collapse; font-size: 10px;
    }
    td {
      /* fix so we can press/hold */
      touch-action: manipulation;
      -webkit-user-select: none;
      user-select: none;
    }
    table tr td:first-child { white-space: nowrap; } /* nowrap on idx */
    th, td { padding: 2px 5px; }
    #error p { background: #fee; padding: 2px 5px; border: 1px solid red; }
    .minimized {
      max-width: 1.5em;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      opacity: 0.6;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <h2>LabelLifter</h2>
  <h3>scanning HDD/SDD/drive labels</h3>
  <h4>using your smarty phone</h4>

  <button id="cameraButton">Take Photo</button>
  <input type="file" accept="image/*" capture="environment" id="cameraInput" style="display: none;"> of
  <input type="number" id="expectedBars" name="expected" min="1" max="9" value="%(expected_bars)s"> barcodes &mdash;

  <button onclick="downloadCSV()">Download CSV</button>

  <div id="error"></div>

  <p>Scan results:</p>
  <div id="tablediv"></div>

  <p>
    <em>Press on columns to minimize them. Press and hold on the first column
    to delete unwanted entries.</em>
  </p>
  <p>
    The barcode scanner will attempt to find various barcodes, QR-codes, and
    Data Matrix (ECC 200) serials on your uploaded photo. The scanner works
    best if you take pictures of the same type of drives; otherwise the table
    layout can look messy.
  </p>
  <p>
    The Data Matrix decoder can be really slow. If you know the total amount of
    barcodes in advance, set it so the scanner can stop looking early.
  </p>

  <script>
    function getNow(withDate) {
        if (withDate) {
          return (new Date().toISOString()).replace(/[^0-9TZ]/g, '');
        }
        return (new Date().toTimeString()).substr(0, 5);
    }
    function insertZwsp(s) {
        //if (s.length > 12)
        //    return s.replace(/(.{8})/g, '$1\\u200B');
        if (s.length > 8)
            return s.replace(/(.{6})/g, '$1\\u200B');
        if (s.length > 6)
            return s.replace(/(.{4})/g, '$1\\u200B');
        return s;
    }

    function downloadCSV() {
      const csv = rows.map(row =>
        row.map(cell => `"${(cell ?? '').toString().replace(/"/g, '""').replace(/\\u200B/g, '')}"`).join(',')
      ).join('\\n');

      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `barcodes-${getNow(true)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }

    const input = document.getElementById('cameraInput');
    let photoFile = null;
    let photoIdx = 0;

    let columns = ['idx'];
    let rows = [];
    let hiddenCols = new Set();

    function toggleColumn(colIndex) {
      if (hiddenCols.has(colIndex)) {
        hiddenCols.delete(colIndex);
      } else {
        hiddenCols.add(colIndex);
      }
      display();
    }

    function addNewRecord(columns, rows, newData) {
      const timestamp = getNow();
      const idx = `${photoIdx}-${timestamp}`;
      photoIdx += 1;

      newData.splice(0, 0, ['idx', idx]);

      // Map column names to values in the order they appear in newData
      const valuesByCol = {};
      for (let [col, val] of newData) {
        if (col == 'code-39')
          col = 'c39';

        if (!valuesByCol[col])
          valuesByCol[col] = [];
        valuesByCol[col].push(val);

        // Add new column names if not already in columns (even duplicates OK,
        // but don't re-add existing ones)
        const existingCount = columns.filter(c => c === col).length;
        const newCount = valuesByCol[col].length;
        for (i = 0; i < (newCount - existingCount); ++i) {
          columns.push(col);
        }
      }

      // Build a new row with the right length
      const newRow = [];
      const colCounts = {}; // track which instance we're filling
      for (let i = 0; i < columns.length; i++) {
        const col = columns[i];
        const count = colCounts[col] = (colCounts[col] || 0);
        let val = (valuesByCol[col] && valuesByCol[col][count]) || null;
        if (i > 0 && val)
          val = insertZwsp(val); // no breaking in idx
        newRow.push(val);
        colCounts[col]++;
      }

      rows.splice(0, 0, newRow);
    }

    function renderTable(columns, rows) {
      const thead = `<thead><tr>${
        columns.map((col, i) =>
          `<th data-col="${i}" class="${hiddenCols.has(i) ? 'minimized' : ''}">${col}</th>`
        ).join('')
      }</tr></thead>`;

      const tbody = `<tbody>${
        rows.map(row =>
          `<tr>${row.map((cell, i) =>
            `<td data-col="${i}" class="${hiddenCols.has(i) ? 'minimized' : ''}">${cell ?? ''}</td>`
          ).join('')}</tr>`
        ).join('')
      }</tbody>`;

      return `<table>${thead}${tbody}</table>`;
    }

    function display() {
      const div = document.getElementById('tablediv');
      div.innerHTML = renderTable(columns, rows);

      div.querySelectorAll('td, th').forEach(cell => {
        const col = parseInt(cell.dataset.col);

        if (col === 0) {
          // Long press for row deletion
          // TODO: prune columns after deletion!
          let pressTimer;

          const start = () => {
            pressTimer = setTimeout(() => {
              const row = parseInt(cell.parentNode.rowIndex);
              const text = cell.innerHTML;
              gcell = cell;
              if (!isNaN(row) && confirm(`Delete row ${text}`)) {
                rows.splice(row - 1, 1); // row index is +1 because of thead
                display();
              }
            }, 600);
          };

          const cancel = () => clearTimeout(pressTimer);

          // Touch events
          cell.addEventListener('touchstart', start, { passive: true });
          cell.addEventListener('touchend', cancel);
          cell.addEventListener('touchmove', cancel, { passive: true });

          // Mouse events (desktop fallback)
          cell.addEventListener('mousedown', start);
          cell.addEventListener('mouseup', cancel);
          cell.addEventListener('mouseleave', cancel);
        } else {
          // Tap to toggle column
          cell.addEventListener('click', () => {
            toggleColumn(col);
          });
        }
      });
    }
    function displayError(error) {
      if (error == null) {
        document.getElementById('error').innerHTML = '';
      } else {
        document.getElementById('error').innerHTML = '<p class="error">' + error + '</p>';
      }
    }

    input.addEventListener('change', (event) => {
      const photoFile = event.target.files[0];
      if (!photoFile) return;

      const formData = new FormData();
      formData.append('photo', photoFile);

      let expected_bars = %(expected_bars)s;
      if (document.getElementById('expectedBars').value.match(/^[0-9]+$/)) {
        expected_bars = Number(document.getElementById('expectedBars').value);
      }

      fetch(`/upload?expected_bars=${expected_bars}`, {
        method: 'POST',
        body: formData
      })
      .then(res => {
        displayError(null); // wipe error
        input.value = ''; // reset upload in all cases
        if (res.ok) {
          console.log('Upload successful!');
        } else {
          console.log('Upload failed.');
        }
        return res.json()
      })
      .then(data => {
        console.log('data', data);
        if (data.error) {
          displayError(data.error);
        } else {
          addNewRecord(columns, rows, data.decoded);
          display();
        }
      })
      .catch(err => {
        displayError(err); // show error
        input.value = ''; // reset upload on error
        alert('Error: ' + err); // this is more severe
      });
    });

    document.getElementById('cameraButton').addEventListener('click', function() {
      input.click();
    });

    addNewRecord(columns, rows, []);
    //addNewRecord(columns, rows, [['a', 'A1'], ['a', 'A1'], ['b', 'B1']]);
    //addNewRecord(columns, rows, [['b', 'B1']]);
    display();
  </script>
</body>
</html>
''' % {'expected_bars': expected_bars}


@app.route('/upload', methods=['POST'])
def upload():
    if 'photo' not in request.files:
        return jsonify({'error': 'no file'}), 400

    try:
        expected_bars = int(request.args.get('expected_bars', '') or 5)
    except ValueError:
        expected_bars = 5

    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'empty filename'}), 400

    # recorded.append(f'{len(recorded) + 1} new photo')

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'input.jpg')
        file.save(filepath)

        # Example: convert image to grayscale
        gray_path = os.path.join(tmpdir, 'gray.jpg')
        try:
            bars = []

            # =================================================
            # Normalize/stretch the contrast for better reading
            # =================================================
            # subprocess.run(
            #     ['timeout', '5s', 'convert', filepath,
            #      '-colorspace', 'Gray',
            #      '-brightness-contrast', '10x20', gray_path],
            #     check=True)
            subprocess.run(
                ['timeout', '5s', 'convert', filepath,
                 '-contrast-stretch', '2%',
                 # For big photos, resize can sharpen things a bit.
                 # 1600x> means max 1600xSOMETHING.
                 '-resize', '1800x>',
                 '-quality', '98',
                 gray_path],
                check=True)

            # ================================================
            # Use zbarimg to find qr-codes and other bar codes
            # ================================================
            zbar_result = subprocess.run(
                ['timeout', '3s', 'zbarimg', gray_path],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True)
            zbar_result = zbar_result.stdout.strip()
            print('DEBUG: zbar', repr(zbar_result), file=sys.stderr)
            if zbar_result:
                for zbar in zbar_result.split('\n'):
                    try:
                        colname, colvalue = zbar.split(':', 1)
                    except ValueError:
                        colname, colvalue = 'error', zbar
                    bars.append((colname.lower(), colvalue))

            # ==========================================
            # Use dmtxread to find data matrix bar codes
            # ==========================================
            # DMTX reading can be really slow. We'll want to scan at most how
            # many barcodes we expect.
            expected_bars = max(1, expected_bars - len(bars))
            dmtx_result = subprocess.run(
                ['timeout', f'{expected_bars + 1}s', 'dmtxread', '-n',
                 f'-m{expected_bars}500', f'-N{expected_bars}', gray_path],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True)
            dmtx_result = dmtx_result.stdout.strip()
            print('DEBUG: dmtx', repr(dmtx_result), file=sys.stderr)
            if dmtx_result:
                for dmtx in dmtx_result.split('\n'):
                    bars.append(('dmtx', dmtx))

            if not bars:
                return jsonify({'error': 'no barcodes found'}), 500

            print('BARS', bars, file=sys.stderr)
            return jsonify({
                'message': 'processed',
                'decoded': bars,
            })

        except subprocess.CalledProcessError as e:
            return jsonify({'error': str(e), 'stderr': e.stderr}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
