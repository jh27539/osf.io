# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-04-19 22:43
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0120_merge_20180716_1457'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='abstractnode',
            name='wiki_pages_current',
        ),
        migrations.RemoveField(
            model_name='abstractnode',
            name='wiki_pages_versions',
        ),
    ]
