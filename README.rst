LabelLifter
===========

*Need to scan barcodes and labels from a stack of hard drives?*

**LabelLifter** captures photos, extracts barcodes, and compiles the
results into a downloadable CSV.


------------
How it works
------------

**LabelLifter** combines a lightweight modern **JavaScript** frontend —
usable from your smartphone — with a backend Docker image.

The backend uses ``zbarimg(1)`` and ``dmtxread(1)`` to decode various
barcode formats from images.

Workflow:

- Take a picture of the drive;
- Upload it to the backend;
- Barcodes and text are extracted automatically;
- Repeat for more drives;
- Download your CSV when done.

The interface groups similar barcode types together. If you're scanning
multiple drives of the same model, corresponding barcodes will appear
consistently in the same columns.


----
Bugs
----

Not much effort has been spent to get the best results for a wide range
of images. Use proper lighting and a proper distance when taking photos.
Improvements (with test images) are welcome.


-----------
Screenshots
-----------

**See these screenshots as an example.**

+---------------------------------------+---------------------------------------+
| Start in the interface.               | Take a photo and upload it.           |
| Click "Take Photo".                   |                                       |
|                                       |                                       |
| .. image:: assets/scanner-initial.png | .. image:: assets/scanner-photo.png   |
+---------------------------------------+---------------------------------------+
| The actual photo.                     | The results in the dynamic table.     |
|                                       | Additional uploads will add more      |
|                                       | rows at the top.                      |
|                                       |                                       |
| .. image:: assets/scanner-input.jpg   | .. image:: assets/scanner-scanned.png |
|   :width: 360                         |                                       |
+---------------------------------------+---------------------------------------+
| After clicking "Download CSV", you can see this:                              |
|                                                                               |
| .. image:: assets/scanner-csvresult.png                                       |
+-----------------------------------------+-------------------------------------+

**Example CSV output:**

.. code-block:: csv

   "1-20:47","https://tags.osso.nl/hdd/YCYKUGXVZCTO9VFFPDNC/","PHWA604305QY240AGN","H69280-301","55CD2E404C6EEB7E"
   "0-20:46"


-------
License
-------

GNU General Public License version 3.
