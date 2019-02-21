import functools
import io
import logging
import matplotlib
import numpy
import operator
import os
import zipfile

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.forms import formset_factory
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.shortcuts import reverse
from django.views import generic

from accounts.models import UserProfile
from mainproject import settings
from materials import forms
from materials import models
import materials.rangeparser


matplotlib.use('Agg')
logger = logging.getLogger(__name__)


def data_dl(request, type_, id_, bandgap=False):
    """Download a specific entry type"""
    response = HttpResponse(content_type='text/fhi-aims')
    if type_ == 'band_gap':
        type_ = 'band_structure'
        bandgap = True

    def write_headers():
        if type_ not in ['all_atomic_positions']:
            if not bandgap:
                response.write(str('#HybriD³ Materials Database\n'))
            response.write(str('\n#System: '))
            response.write(str(p_obj.compound_name))
        response.write(str('\n#Temperature: '))
        response.write(str(obj.temperature + ' K'))
        response.write(str('\n#Phase: '))
        response.write(str(obj.phase.phase))
        authors = obj.publication.author_set.all()
        response.write(str('\n#Authors ('+str(authors.count())+'): '))
        for author in authors:
            response.write('\n    ')
            response.write(author.first_name + ' ')
            response.write(author.last_name)
            response.write(', ' + author.institution)
        response.write(str('\n#Journal: '))
        response.write(str(obj.publication.journal))
        response.write(str('\n#Source: '))
        if obj.publication.doi_isbn:
            response.write(str(obj.publication.doi_isbn))
        else:
            response.write(str('N/A'))

    def write_a_pos():
        response.write('\n#a: ')
        response.write(obj.a)
        response.write('\n#b: ')
        response.write(obj.b)
        response.write('\n#c: ')
        response.write(obj.c)
        response.write('\n#alpha: ')
        response.write(obj.alpha)
        response.write('\n#beta: ')
        response.write(obj.beta)
        response.write('\n#gamma: ')
        response.write(obj.gamma)
        response.write('\n\n')

    if type_ == 'atomic_positions':
        obj = models.AtomicPositions.objects.get(id=id_)
        p_obj = models.System.objects.get(atomicpositions=obj)
        write_headers()
        write_a_pos()
        fileloc = (settings.MEDIA_ROOT + '/uploads/%s_%s_%s_apos.in' %
                   (obj.phase, p_obj.organic, p_obj.inorganic))
        if(os.path.isfile(fileloc)):
            with open(fileloc, encoding='utf-8', mode='r+') as f:
                lines = f.read().splitlines()
                for line in lines:
                    response.write(line + '\n')
        else:
            response.write('#-Atomic Positions input file not available-')
        response['Content-Disposition'] = (
            'attachment; filename=%s_%s_%s_%s.in' % (obj.phase, p_obj.organic,
                                                     p_obj.inorganic, type_))
    elif type_ == 'all_atomic_positions':  # all the a_pos entries
        p_obj = models.System.objects.get(id=id_)
        response.write(str('#HybriD³ Materials Database\n\n'))
        name = p_obj.compound_name
        response.write(str('#'*(len(name)+22) + '\n'))
        response.write(str('#####  System: '))
        response.write(str(name))
        response.write(str('  #####\n#' + '#'*(len(name)+22) + '\n'))
        for obj in p_obj.atomicpositions_set.all():
            write_headers()
            write_a_pos()
        response['Content-Disposition'] = (
            'attachment; filename=%s_%s_%s_%s.in' % (obj.phase, p_obj.organic,
                                                     p_obj.inorganic, 'ALL'))
    elif type_ == 'exciton_emission':
        obj = models.ExcitonEmission.objects.get(id=id_)
        p_obj = models.System.objects.get(excitonemission=obj)
        file_name_prefix = '%s_%s_%s_pl' % (obj.phase, p_obj.organic,
                                            p_obj.inorganic)
        dir_in_str = os.path.join(settings.MEDIA_ROOT, 'uploads')
        meta_filename = file_name_prefix + '.txt'
        meta_filepath = os.path.join(dir_in_str, meta_filename)
        with open(meta_filepath, encoding='utf-8', mode='w+') as meta_file:
            meta_file.write(str('#HybriD³ Materials Database\n'))
            meta_file.write(str('\n#System: '))
            meta_file.write(str(p_obj.compound_name))
            meta_file.write(str('\n#Temperature: '))
            meta_file.write(str(obj.temperature))
            meta_file.write(str('\n#Phase: '))
            meta_file.write(str(obj.phase.phase))
            meta_file.write(str('\n#Authors: '))
            for author in obj.publication.author_set.all():
                meta_file.write('\n    ')
                meta_file.write(author.first_name + ' ')
                meta_file.write(author.last_name)
                meta_file.write(', ' + author.institution)
            meta_file.write(str('\n#Journal: '))
            meta_file.write(str(obj.publication.journal))
            meta_file.write(str('\n#Source: '))
            meta_file.write(str(obj.publication.doi_isbn))
            meta_file.write(str('\n#Exciton Emission Peak: '))
            meta_file.write(str(obj.excitonemission))
        pl_file_csv = os.path.join(dir_in_str, file_name_prefix + '.csv')
        pl_file_html = os.path.join(dir_in_str, file_name_prefix + '.html')
        filenames = []
        filenames.append(meta_filepath)
        filenames.append(pl_file_csv)
        filenames.append(pl_file_html)

        zip_dir = file_name_prefix
        zip_filename = '%s.zip' % zip_dir
        # change response type and content deposition type
        string = io.BytesIO()
        zf = zipfile.ZipFile(string, 'w')

        for fpath in filenames:
            # Calculate path for file in zip
            fdir, fname = os.path.split(fpath)
            zip_path = os.path.join(zip_dir, fname)
            zf.write(fpath, zip_path)
        # Must close zip for all contents to be written
        zf.close()
        # Grab ZIP file from in-memory, make response with correct MIME-type
        response = HttpResponse(string.getvalue(),
                                content_type='application/x-zip-compressed')
        response['Content-Disposition'] = ('attachment; filename=%s' %
                                           zip_filename)
    elif type_ == 'synthesis':
        obj = m.SynthesisMethodOld.objects.get(id=id_)
        p_obj = models.System.objects.get(synthesismethod=obj)
        file_name_prefix = '%s_%s_%s_syn' % (obj.phase, p_obj.organic,
                                             p_obj.inorganic)
        meta_filename = file_name_prefix + '.txt'
        response = HttpResponse(content_type='text/plain')
        response.write(str('#HybriD³ Materials Database\n'))
        response.write(str('\n#System: '))
        response.write(str(p_obj.compound_name))
        response.write(str('\n#Temperature: '))
        response.write(str(obj.temperature))
        response.write(str('\n#Phase: '))
        response.write(str(obj.phase.phase))
        response.write(str('\n#Authors: '))
        for author in obj.publication.author_set.all():
            response.write('\n    ')
            response.write(author.first_name + ' ')
            response.write(author.last_name)
            response.write(', ' + author.institution)
        response.write(str('\n#Journal: '))
        response.write(str(obj.publication.journal))
        response.write(str('\n#Source: '))
        response.write(str(obj.publication.doi_isbn))
        if obj.synthesis_method:
            response.write(str('\n#Synthesis Method: '))
            response.write(str(obj.synthesis_method))
        if obj.starting_materials:
            response.write(str('\n#Starting Materials: '))
            response.write(str(obj.starting_materials))
        if obj.remarks:
            response.write(str('\n#Remarks: '))
            response.write(str(obj.remarks))
        if obj.product:
            response.write(str('\n#Product: '))
            response.write(str(obj.product))
        response.encoding = 'utf-8'
        response['Content-Disposition'] = ('attachment; filename=%s' %
                                           (meta_filename))
    elif type_ == 'band_structure' and bandgap:
        obj = models.BandStructure.objects.get(id=id_)
        p_obj = models.System.objects.get(bandstructure=obj)
        filename = '%s_%s_%s_bg.txt' % (obj.phase, p_obj.organic,
                                        p_obj.inorganic)
        response.write(str('#HybriD³ Materials Database\n\n'))
        response.write('****************\n')
        response.write('Band gap: ')
        if obj.band_gap != '':
            response.write(obj.band_gap + ' eV')
        else:
            response.write('N/A')
        response.write('\n****************\n')
        write_headers()
        response.encoding = 'utf-8'
        response['Content-Disposition'] = ('attachment; filename=%s' %
                                           (filename))
    elif type_ == 'band_structure':
        obj = models.BandStructure.objects.get(id=id_)
        p_obj = models.System.objects.get(bandstructure=obj)
        file_name_prefix = '%s_%s_%s_%s_bs' % (obj.phase, p_obj.organic,
                                               p_obj.inorganic, obj.pk)
        dir_in_str = os.path.join(settings.MEDIA_ROOT, obj.folder_location)
        compound_name = dir_in_str.split('/')[-1]
        meta_filename = file_name_prefix + '.txt'
        meta_filepath = os.path.join(dir_in_str, meta_filename)
        with open(meta_filepath, encoding='utf-8', mode='w+') as meta_file:
            meta_file.write('#HybriD3 Materials Database\n')
            meta_file.write('\n#System: ')
            meta_file.write(p_obj.compound_name)
            meta_file.write('\n#Temperature: ')
            meta_file.write(obj.temperature)
            meta_file.write('\n#Phase: ')
            meta_file.write(str(obj.phase.phase))
            meta_file.write(str('\n#Authors: '))
            for author in obj.publication.author_set.all():
                meta_file.write('\n    ')
                meta_file.write(author.first_name + ' ')
                meta_file.write(author.last_name)
                meta_file.write(', ' + author.institution)
            meta_file.write('\n#Journal: ')
            meta_file.write(str(obj.publication.journal))
            meta_file.write('\n#Source: ')
            meta_file.write(str(obj.publication.doi_isbn))
        bs_full = os.path.join(dir_in_str, file_name_prefix + '_full.png')
        bs_mini = os.path.join(dir_in_str, file_name_prefix + '_min.png')
        filenames = []
        filenames.append(bs_full)
        filenames.append(bs_mini)
        for f in os.listdir(dir_in_str):
            filename = os.fsdecode(f)
            if filename.endswith('.in') or filename.endswith('.out') or (
                    filename.endswith('.txt')):
                full_filename = os.path.join(dir_in_str, filename)
                filenames.append(full_filename)
        zip_dir = compound_name
        zip_filename = '%s.zip' % zip_dir
        # change response type and content deposition type
        string = io.BytesIO()
        zf = zipfile.ZipFile(string, 'w')

        for fpath in filenames:
            # Calculate path for file in zip
            fdir, fname = os.path.split(fpath)
            zip_path = os.path.join(zip_dir, fname)
            zf.write(fpath, zip_path)
        # Must close zip for all contents to be written
        zf.close()
        # Grab ZIP file from in-memory, make response with correct MIME-type
        response = HttpResponse(string.getvalue(),
                                content_type='application/x-zip-compressed')
        response['Content-Disposition'] = ('attachment; filename=%s' %
                                           zip_filename)
    elif type_ == 'input_files':
        obj = models.BandStructure.objects.get(id=id_)
        p_obj = models.System.objects.get(bandstructure=obj)
        file_name_prefix = '%s_%s_%s_%s_bs' % (obj.phase, p_obj.organic,
                                               p_obj.inorganic, obj.pk)
        dir_in_str = os.path.join(settings.MEDIA_ROOT, obj.folder_location)
        compound_name = dir_in_str.split('/')[-1]
        filenames = []
        for F in ('control.in', 'geometry.in'):
            if os.path.exists(f'{dir_in_str}/{F}'):
                filenames.append(f'{dir_in_str}/{F}')
        zip_dir = compound_name
        zip_filename = f'{zip_dir}.zip'
        # change response type and content deposition type
        string = io.BytesIO()
        zf = zipfile.ZipFile(string, 'w')
        for fpath in filenames:
            fdir, fname = os.path.split(fpath)
            zip_path = os.path.join(zip_dir, fname)
            zf.write(fpath, zip_path)
        # Must close zip for all contents to be written
        zf.close()
        # Grab ZIP file from in-memory, make response with correct MIME-type
        response = HttpResponse(string.getvalue(),
                                content_type='application/x-zip-compressed')
        response['Content-Disposition'] = ('attachment; filename=%s' %
                                           zip_filename)
    return response


def all_a_pos(request, id_):
    """Defines views for each specific entry type."""
    def sortEntries(entry):
        """Sort by temperature, but temperature is a charFields"""
        try:
            return int(entry.temperature)
        except Exception:
            # temperature field contains something other than digits (e.g. N/A)
            temp = ''
            for c in entry.temperature:
                if c.isdigit():
                    temp += c
                else:
                    if temp != '':
                        return int(temp)
            # no temperature, so make this entry last
            return 9999999

    template_name = 'materials/all_a_pos.html'
    obj = models.System.objects.get(id=id_)
    compound_name = models.System.objects.get(id=id_).compound_name
    obj = obj.atomicpositions_set.all()
    obj = sorted(obj, key=sortEntries)
    return render(request, template_name,
                  {'object': obj, 'compound_name': compound_name, 'key': id_})


def all_entries(request, id_, type_):
    str_to_model = {
        'atomic_positions': models.AtomicPositions,
        'exciton_emission': models.ExcitonEmission,
        'synthesis': models.SynthesisMethodOld,
        'band_structure': models.BandStructure,
        'material_prop': models.MaterialProperty
    }
    template_name = 'materials/all_%ss.html' % type_
    compound_name = models.System.objects.get(pk=id_).compound_name
    obj = str_to_model[type_].objects.filter(system__id=id_)
    return render(request, template_name,
                  {'object': obj, 'compound_name': compound_name,
                   'data_type': type_, 'key': id_})


def getAuthorSearchResult(search_text):
    keyWords = search_text.split()
    results = models.System.objects.\
        filter(functools.reduce(operator.or_, (
            Q(atomicpositions__publication__author__last_name__icontains=x) for
            x in keyWords)) | functools.reduce(operator.or_, (
                Q(synthesismethod__publication__author__last_name__icontains=x)
                for x in keyWords)) | functools.reduce(operator.or_, (
                        Q(excitonemission__publication__author__last_name__icontains=x)
                        for x in keyWords)) | functools.reduce(operator.or_, (
                                Q(bandstructure__publication__author__last_name__icontains=x)
                                for x in keyWords))
         ).distinct()
    return results


def search_result(search_term, search_text):
    if search_term == 'formula':
        return models.System.objects.filter(
            Q(formula__icontains=search_text) |
            Q(group__icontains=search_text) |
            Q(compound_name__icontains=search_text)).order_by('formula')
    elif search_term == 'organic':
        return models.System.objects.filter(
            organic__icontains=search_text).order_by('organic')
    elif search_term == 'inorganic':
        return models.System.objects.filter(
            inorganic__icontains=search_text).order_by('inorganic')
    elif search_term == 'author':
        return getAuthorSearchResult(search_text)
    else:
        raise KeyError('Invalid search term.')


class SearchFormView(generic.TemplateView):
    """Search for system page"""
    template_name = 'materials/search.html'
    search_terms = [
        ['formula', 'Formula'],
        ['organic', 'Organic Component'],
        ['inorganic', 'Inorganic Component'],
        ['exciton_emission', 'Exciton Emission'],
        ['author', 'Author']
    ]

    def get(self, request):
        return render(request, self.template_name,
                      {'search_terms': self.search_terms})

    def post(self, request):
        template_name = 'materials/search_results.html'
        form = forms.SearchForm(request.POST)
        search_text = ''
        # default search_term
        search_term = 'formula'
        if form.is_valid():
            search_text = form.cleaned_data['search_text']
            search_term = request.POST.get('search_term')
            systems_info = []
            if search_term == 'exciton_emission':
                searchrange = materials.rangeparser.parserange(search_text)
                if len(searchrange) > 0:
                    if searchrange[0] == 'bidirectional':
                        if searchrange[3] == '>=':
                            systems = models.ExcitonEmission.objects.filter(
                                exciton_emission__gte=searchrange[1]).order_by(
                                    '-exciton_emission')
                        elif searchrange[3] == '>':
                            systems = models.ExcitonEmission.objects.filter(
                                exciton_emission__gt=searchrange[1]).order_by(
                                    '-exciton_emission')
                        if searchrange[4] == '<=':
                            systems = systems.filter(
                                exciton_emission__lte=searchrange[2]).order_by(
                                    '-exciton_emission')
                        elif searchrange[4] == '<':
                            systems = systems.filter(
                                exciton_emission__lt=searchrange[2]).order_by(
                                    '-exciton_emission')
                    elif searchrange[0] == 'unidirectional':
                        if searchrange[2] == '>=':
                            systems = models.ExcitonEmission.objects.filter(
                                exciton_emission__gte=searchrange[1]).order_by(
                                    '-exciton_emission')
                        elif searchrange[2] == '>':
                            systems = models.ExcitonEmission.objects.filter(
                                exciton_emission__gt=searchrange[1]).order_by(
                                    '-exciton_emission')
                        elif searchrange[2] == '<=':
                            systems = models.ExcitonEmission.objects.filter(
                                exciton_emission__lte=searchrange[1]).order_by(
                                    '-exciton_emission')
                        elif searchrange[2] == '<':
                            systems = models.ExcitonEmission.objects.filter(
                                exciton_emission__lt=searchrange[1]).order_by(
                                    '-exciton_emission')
                    for ee in systems:
                        system_info = {}
                        system_info['compound_name'] = ee.system.compound_name
                        system_info['common_formula'] = ee.system.group
                        system_info['chemical_formula'] = ee.system.formula
                        system_info['ee'] = str(ee.exciton_emission)
                        system_info['sys_pk'] = ee.system.pk
                        system_info['ee_pk'] = ee.pk
                        if ee.system.synthesismethod_set.count() > 0:
                            system_info['syn_pk'] = (
                                ee.system.synthesismethod_set.first().pk)
                        else:
                            system_info['syn_pk'] = 0
                        if ee.system.atomicpositions_set.count() > 0:
                            system_info['apos_pk'] = (
                                ee.system.atomicpositions_set.first().pk)
                        else:
                            system_info['apos_pk'] = 0
                        if ee.system.bandstructure_set.count() > 0:
                            system_info['bs_pk'] = (
                                ee.system.bandstructure_set.first().pk)
                        else:
                            system_info['bs_pk'] = 0
                        systems_info.append(system_info)
            else:
                systems = search_result(search_term, search_text)

        args = {
            'systems': systems,
            'search_term': search_term,
            'systems_info': systems_info
        }
        return render(request, template_name, args)


def makeCorrections(form):
    # alter user input if necessary
    try:
        temp = form.temperature
        if temp.endswith('K') or temp.endswith('C'):
            temp = temp[:-1].strip()
            form.temperature = temp
        return form
    except Exception:  # just in case
        return form


class AddAPosView(generic.TemplateView):
    template_name = 'materials/add_a_pos.html'

    def get(self, request):
        search_form = forms.SearchForm()
        a_pos_form = forms.AddAtomicPositions()
        return render(request, self.template_name, {
            'search_form': search_form,
            'a_pos_form': a_pos_form,
            'initial_state': True,
            # determines whether this field appears on the form
            'related_synthesis': True
        })

    def post(self, request):
        form = forms.AddAtomicPositions(request.POST, request.FILES)
        if form.is_valid():
            apos_form = form.save(commit=False)
            pub_pk = request.POST.get('publication')
            sys_pk = request.POST.get('system')
            syn_pk = request.POST.get('synthesis-methods')
            try:
                apos_form.synthesis_method = (
                    models.SynthesisMethodOld.objects.get(pk=int(syn_pk)))
            except Exception:
                # no synthesis method was chosen (or maybe an error occurred)
                pass
            if int(pub_pk) > 0 and int(sys_pk) > 0:
                apos_form.publication = models.Publication.objects.get(pk=pub_pk)
                apos_form.system = models.System.objects.get(pk=sys_pk)
                if request.user.is_authenticated:
                    apos_form.contributor = UserProfile.objects.get(
                        user=request.user)
                    text = 'Save success!'
                    feedback = 'success'
                    apos_form = makeCorrections(apos_form)
                    apos_form.save()
                else:
                    text = 'Failed to submit, please login and try again.'
                    feedback = 'failure'
        else:
            text = 'Failed to submit, please fix the errors, and try again.'
            feedback = 'failure'

        args = {'feedback': feedback, 'text': text}

        return JsonResponse(args)


class AddPubView(generic.TemplateView):
    template_name = 'materials/add_publication.html'

    def get(self, request):
        search_form = forms.SearchForm()
        pub_form = forms.AddPublication()
        return render(request, self.template_name, {
            'search_form': search_form,
            'pub_form': pub_form,
            'initial_state': True
        })

    def post(self, request):
        authors_info = {}
        for key in request.POST:
            if key.startswith('form-'):
                value = request.POST[key].strip()
                authors_info[key] = value
                if value == '':
                    return JsonResponse(
                        {'feedback': 'failure',
                         'text': ('Failed to submit, '
                                  'author information is incomplete.')})
        # sanity check: each author must have first name, last name,
        # institution
        assert(len(authors_info) % 3 == 0)
        author_count = len(authors_info) // 3
        pub_form = forms.AddPublication(request.POST)
        if pub_form.is_valid():
            form = pub_form.save(commit=False)
            doi_isbn = pub_form.cleaned_data['doi_isbn']
            # check if doi_isbn is unique/valid, except when field is empty
            if len(doi_isbn) == 0 or len(
                    models.Publication.objects.filter(doi_isbn=doi_isbn)) == 0:
                form.author_count = author_count
                form.save()
                newPub = form
                text = 'Save success!'
                feedback = 'success'
            else:
                text = 'Failed to submit, publication is already in database.'
                feedback = 'failure'
        else:
            text = 'Failed to submit, please fix the errors, and try again.'
            feedback = 'failure'
        if feedback == 'failure':
            return JsonResponse({'feedback': feedback, 'text': text})
        # create and save new author objects, linking them to the
        # saved publication
        for i in range(author_count):  # for each author
            data = {}
            data['first_name'] = authors_info['form-%d-first_name' % i]
            data['last_name'] = authors_info['form-%d-last_name' % i]
            data['institution'] = authors_info['form-%d-institution' % i]
            preexistingAuthors = (
                models.Author.objects.filter(
                    first_name__iexact=data['first_name']).filter(
                        last_name__iexact=data['last_name']).filter(
                            institution__iexact=data['institution']))
            if preexistingAuthors.count() > 0:
                # use the prexisting author object
                preexistingAuthors[0].publication.add(newPub)
            else:  # this is a new author, so create a new object
                author_form = forms.AddAuthor(data)
                if(not author_form.is_valid()):
                    text = ('Failed to submit, author not valid. '
                            'Please fix the errors, and try again.')
                    feedback = 'failure'
                    break
                else:  # author_form is valid
                    form = author_form.save()
                    form.publication.add(newPub)
                    form.save()
                    text = 'Save success!'
                    feedback = 'success'
        args = {
                # 'search_form': search_form,
                # 'pub_form': pub_form,
                'feedback': feedback,
                'text': text,
                # 'initial_state': True,
                }
        # return render(request, self.template_name, args)
        # ajax version below
        return JsonResponse(args)


class SearchPubView(generic.TemplateView):
    template_name = 'materials/dropdown_list_pub.html'

    def post(self, request):
        search_form = forms.SearchForm(request.POST)
        search_text = ''
        if search_form.is_valid():
            search_text = search_form.cleaned_data['search_text']
            author_search = (
                models.Publication.objects.filter(
                    Q(author__first_name__icontains=search_text) |
                    Q(author__last_name__icontains=search_text) |
                    Q(author__institution__icontains=search_text)).distinct())
            if len(author_search) > 0:
                search_result = author_search
            else:
                search_result = models.Publication.objects.filter(
                    Q(title__icontains=search_text) |
                    Q(journal__icontains=search_text)
                )
        return render(request, self.template_name,
                      {'search_result': search_result})


class AddAuthorsToPublicationView(generic.TemplateView):
    template_name = 'materials/add_authors_to_publication.html'

    def post(self, request):
        author_count = request.POST['author_count']
        # variable number of author forms
        author_formset = formset_factory(forms.AddAuthor, extra=int(author_count))
        return render(request, self.template_name,
                      {'entered_author_count': author_count,
                       'author_formset': author_formset})


class SearchAuthorView(generic.TemplateView):
    """This is for add publication page"""
    # template_name = 'materials/add_publication.html'
    template_name = 'materials/dropdown_list_author.html'

    def post(self, request):
        search_form = forms.SearchForm(request.POST)
        # pub_form = forms.AddPublication()
        search_text = ''
        if search_form.is_valid():
            search_text = search_form.cleaned_data['search_text']
            search_result = models.Author.objects.filter(
                Q(first_name__icontains=search_text) |
                Q(last_name__icontains=search_text) |
                Q(institution__icontains=search_text))
            # add last_name filter
        # args = {
        #     'search_form': search_form,
        #     'search_result': search_result,
        #     'pub_form': pub_form
        # }
        # return render(request, self.template_name, args)
        # ajax version
        return render(request, self.template_name,
                      {'search_result': search_result})


class AddAuthorView(generic.TemplateView):
    template_name = 'materials/add_author.html'

    def get(self, request):
        input_form = forms.AddAuthor()
        return render(request, self.template_name, {
            'input_form': input_form,
        })

    def post(self, request):
        # search_form = forms.SearchForm()
        input_form = forms.AddAuthor(request.POST)
        if input_form.is_valid():
            first_name = input_form.cleaned_data['first_name'].lower()
            last_name = input_form.cleaned_data['last_name'].lower()
            institution = input_form.cleaned_data['institution'].lower()
            # checks to see if the author is already in database
            q_set_len = len(
                models.Author.objects.filter(first_name__iexact=first_name)
                .filter(last_name__iexact=last_name)
                .filter(institution__icontains=institution)
                )
            if q_set_len == 0:
                input_form.save()
                text = 'Author successfully added!'
                feedback = 'success'
            else:
                text = 'Failed to submit, author is already in database.'
                feedback = 'failure'
        else:
            text = 'Failed to submit, please fix the errors, and try again.'
            feedback = 'failure'
        args = {
                # 'input_form': input_form,
                'feedback': feedback,
                'text': text
                }
        return JsonResponse(args)


class AddTagView(generic.TemplateView):
    template_name = 'materials/add_tag.html'

    def get(self, request):
        input_form = forms.AddTag()
        return render(request, self.template_name, {
            'input_form': input_form,
        })

    def post(self, request):
        # search_form = forms.SearchForm()
        input_form = forms.AddTag(request.POST)
        if input_form.is_valid():
            tag = input_form.cleaned_data['tag'].lower()
            q_set_len = len(
                models.Tag.objects.filter(tag__iexact=tag)
                )
            if q_set_len == 0:
                input_form.save()
                text = 'Tag successfully added!'
                feedback = 'success'
            else:
                text = 'Failed to submit, tag is already in database.'
                feedback = 'failure'
        else:
            text = 'Failed to submit, please fix the errors, and try again.'
            feedback = 'failure'
        args = {
                'feedback': feedback,
                'text': text
                }
        return JsonResponse(args)


class SearchSystemView(generic.TemplateView):
    template_name = 'materials/dropdown_list_system.html'

    def post(self, request):
        form = forms.SearchForm(request.POST)
        related_synthesis = ('related_synthesis' in request.POST and
                             request.POST['related_synthesis'] == 'True')
        search_text = ''
        if form.is_valid():
            search_text = form.cleaned_data['search_text']
        search_result = models.System.objects.filter(
            Q(compound_name__icontains=search_text) |
            Q(group__icontains=search_text) |
            Q(formula__icontains=search_text)
        )
        # ajax version
        return render(request, self.template_name,
                      {'search_result': search_result,
                       'related_synthesis': related_synthesis})


class AddSystemView(generic.TemplateView):
    template_name = 'materials/add_system.html'

    def get(self, request):
        form = forms.AddSystem()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = forms.AddSystem(request.POST)
        if form.is_valid():
            compound_name = form.cleaned_data['compound_name'].lower()
            formula = form.cleaned_data['formula'].lower()
            # checks to see if the author is already in database
            q_set_len = len(
                models.System.objects.filter(
                    Q(compound_name__iexact=compound_name) |
                    Q(formula__iexact=formula)
                )
            )
            if q_set_len == 0:
                form.save()
                text = 'System successfully added!'
                feedback = 'success'
            else:
                text = 'Failed to submit, system is already in database.'
                feedback = 'failure'
        else:
            # return render(request, self.template_name, {'form': form})
            text = 'Failed to submit, please fix the errors, and try again.'
            feedback = 'failure'
        args = {'feedback': feedback, 'text': text}
        return JsonResponse(args)


class AddPhase(generic.TemplateView):
    template_name = 'materials/form.html'

    def get(self, request):
        form = forms.AddPhase()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = forms.AddPhase(request.POST)
        if form.is_valid():
            form.save()
            text = form.cleaned_data['email']
        args = {'form': form, 'text': text}
        return render(request, self.template_name, args)


class AddTemperature(generic.TemplateView):
    template_name = 'materials/form.html'

    def get(self, request):
        form = forms.AddTemperature()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = forms.AddTemperature(request.POST)
        if form.is_valid():
            form.save()
            text = form.cleaned_data['email']

        args = {'form': form, 'text': text}

        return render(request, self.template_name, args)


class AddExcitonEmissionView(generic.TemplateView):
    template_name = 'materials/add_exciton_emission.html'

    def get(self, request):
        search_form = forms.SearchForm()
        exciton_emission_form = forms.AddExcitonEmission()
        return render(request, self.template_name, {
            'search_form': search_form,
            'exciton_emission_form': exciton_emission_form,
            'initial_state': True,
            # determines whether this field appears on the form
            'related_synthesis': True
        })

    def post(self, request):
        form = forms.AddExcitonEmission(request.POST, request.FILES)
        if form.is_valid():
            new_form = form.save(commit=False)
            pub_pk = request.POST.get('publication')
            sys_pk = request.POST.get('system')
            # print 'file: ', request.FILES.get('pl_file')
            syn_pk = request.POST.get('synthesis-methods')
            try:
                new_form.synthesis_method = models.SynthesisMethodOld.objects.get(
                    pk=int(syn_pk))
            except Exception:
                # no synthesis method was chosen (or maybe an error occurred)
                pass
            if int(pub_pk) > 0 and int(sys_pk) > 0:
                new_form.publication = models.Publication.objects.get(pk=pub_pk)
                new_form.system = models.System.objects.get(pk=sys_pk)
                # text += 'Publication and System obtained, '
                if request.user.is_authenticated:
                    new_form.contributor = UserProfile.objects.get(
                        user=request.user)
                    # print apos_form.contributor
                    text = 'Save success!'
                    feedback = 'success'
                    ee_model = new_form.save()
                else:
                    text = 'Failed to submit, please login and try again.'
                    feedback = 'failure'
        else:
            text = 'Failed to submit, please fix the errors, and try again.'
            feedback = 'failure'

        args = {'feedback': feedback, 'text': text}
        return JsonResponse(args)


class AddSynthesisMethodView(generic.TemplateView):
    template_name = 'materials/add_synthesis.html'

    def get(self, request):
        search_form = forms.SearchForm()
        synthesis_form = forms.AddSynthesisMethod()
        return render(request, self.template_name, {
            'search_form': search_form,
            'synthesis_form': synthesis_form,
            'initial_state': True,
            # determines whether this field appears on the form
            'related_synthesis': False
        })

    def post(self, request):
        form = forms.AddSynthesisMethod(request.POST, request.FILES)
        if form.is_valid():
            new_form = form.save(commit=False)
            pub_pk = request.POST.get('publication')
            sys_pk = request.POST.get('system')
            # text = ''
            if int(pub_pk) > 0 and int(sys_pk) > 0:
                new_form.publication = models.Publication.objects.get(pk=pub_pk)
                new_form.system = models.System.objects.get(pk=sys_pk)
                # text += 'Publication and System obtained, '
                if request.user.is_authenticated:
                    new_form.contributor = UserProfile.objects.get(
                        user=request.user)
                    # print apos_form.contributor
                    new_form = makeCorrections(new_form)
                    text = 'Save success!'
                    feedback = 'success'
                    new_form.save()
                else:
                    text = 'Failed to submit, please login and try again.'
                    feedback = 'failure'
        else:
            text = 'Failed to submit, please fix the errors, and try again.'
            feedback = 'failure'

        args = {'feedback': feedback, 'text': text}

        return JsonResponse(args)


class AddBandStructureView(generic.TemplateView):
    template_name = 'materials/add_band_structure.html'

    def get(self, request):
        search_form = forms.SearchForm()
        band_structure_form = forms.AddBandStructure()
        return render(request, self.template_name, {
            'search_form': search_form,
            'band_structure_form': band_structure_form,
            'initial_state': True,
            # determines whether this field appears on the form
            'related_synthesis': True
        })

    def post(self, request):
        form = forms.AddBandStructure(request.POST, request.FILES)
        if form.is_valid():
            new_form = form.save(commit=False)
            pub_pk = request.POST.get('publication')
            sys_pk = request.POST.get('system')
            syn_pk = request.POST.get('synthesis-methods')
            try:
                new_form.synthesis_method = models.SynthesisMethodOld.objects.get(
                    pk=int(syn_pk))
            except Exception:
                # no synthesis method was chosen (or maybe an error occurred)
                pass
            if int(pub_pk) > 0 and int(sys_pk) > 0:
                new_form.publication = models.Publication.objects.get(pk=pub_pk)
                new_form.system = models.System.objects.get(pk=sys_pk)
                # text += 'Settings ready. '
                if request.user.is_authenticated:
                    new_form.contributor = UserProfile.objects.get(
                        user=request.user)
                    # save so a pk can be created for use in the
                    # folder location
                    new_form.save()
                    bs_folder_loc = ('uploads/%s_%s_%s_%s_bs' %
                                     (new_form.phase, new_form.system.organic,
                                      new_form.system.inorganic, new_form.pk))
                    new_form.folder_location = bs_folder_loc
                    try:
                        os.mkdir(bs_folder_loc)
                    except Exception:
                        pass
                    band_files = request.FILES.getlist('band_structure_files')
                    control_file = request.FILES.get('control_in_file')
                    geometry_file = request.FILES.get('geometry_in_file')
                    band_files.append(control_file)
                    band_files.append(geometry_file)
                    for f in band_files:
                        filename = f.name
                        full_filename = os.path.join(bs_folder_loc, filename)
                        with open(full_filename, 'wb+') as write_bs:
                            for chunk in f.chunks():
                                write_bs.write(chunk)
                    # have a script that goes through the band gaps
                    # and spits out some states set plotstate field to
                    # False, save once done, tell user that upload is
                    # successful after this thing, call another
                    # function that plots the BS. Once done, update
                    # the plotted state to done plotbs(bs_folder_loc)
                    new_form = makeCorrections(new_form)
                    text = 'Save success!'
                    feedback = 'success'
                    new_form.save()
                else:
                    text = 'Failed to submit, please login and try again.'
                    feedback = 'failure'
        else:
            text = 'Failed to submit, please fix the errors, and try again.'
            feedback = 'failure'

        args = {'feedback': feedback, 'text': text}

        return JsonResponse(args)


class AddMaterialPropertyView(generic.TemplateView):
    template_name = 'materials/add_material_property.html'

    def get(self, request):
        search_form = forms.SearchForm()
        material_property_form = forms.AddMaterialProperty()
        return render(request, self.template_name, {
            'search_form': search_form,
            'material_property_form': material_property_form,
            'initial_state': True,
            # determines whether this field appears on the form
            'related_synthesis': False
        })

    def post(self, request):
        form = forms.AddMaterialProperty(request.POST)
        if form.is_valid():
            new_form = form.save(commit=False)
            pub_pk = request.POST.get('publication')
            sys_pk = request.POST.get('system')
            if int(pub_pk) > 0 and int(sys_pk) > 0:
                new_form.publication = models.Publication.objects.get(pk=pub_pk)
                new_form.system = models.System.objects.get(pk=sys_pk)
                if request.user.is_authenticated:
                    new_form.contributor = UserProfile.objects.get(
                        user=request.user)
                    new_form = makeCorrections(new_form)
                    text = 'Save success!'
                    feedback = 'success'
                    new_form.save()
                else:
                    text = 'Failed to submit, please login and try again.'
                    feedback = 'failure'
        else:
            text = 'Failed to submit, please fix the errors, and try again.'
            feedback = 'failure'

        args = {'feedback': feedback, 'text': text}

        return JsonResponse(args)


class AddBondLength(generic.TemplateView):
    template_name = 'materials/form.html'

    def get(self, request):
        form = forms.AddBondLength()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = forms.AddBondLength(request.POST)
        if form.is_valid():
            form.save()
            text = form.cleaned_data['email']

        args = {'form': form, 'text': text}

        return render(request, self.template_name, args)


class AddDataView(generic.TemplateView):
    template_name = 'materials/add_data.html'

    def get(self, request):
        return render(request, self.template_name, {
            'publications': models.Publication.objects.all().order_by('year'),
            'systems': models.System.objects.all(),
            'properties': models.Property.objects.all(),
            'units': models.Unit.objects.all(),
            'sample_types': models.Dataset.SAMPLE_TYPES,
            'crystal_systems': models.Dataset.CRYSTAL_SYSTEMS,
        })


def add_property(request):
    property_name = request.POST['property-name']
    prop = models.Property()
    prop.name = property_name
    prop.save(request.user)
    messages.success(request,
                     f'New property "{property_name}" successfully added to '
                     'the database!')
    return redirect(reverse('materials:add_data'))


def add_unit(request):
    unit_name = request.POST['unit-label']
    unit = models.Unit()
    unit.label = unit_name
    unit.save(request.user)
    messages.success(request,
                     f'New unit "{unit_name}" successfully added to '
                     'the database!')
    return redirect(reverse('materials:add_data'))


def submit_data(request):
    """Primary function for submitting data from the user."""
    def add_comment(model, label):
        """Shortcut for conditionally attaching comments to a model instance.

        The purpose of this shortcut is to avoid checking the presence
        of a particular type of comment in POST and the created_by
        and updated_by fields with every call.

        """
        if label in request.POST:
            model.comment_set.create(text=request.POST[label],
                                     created_by=request.user,
                                     updated_by=request.user)
            logger.info(f'Creating {label} comment '
                        f'#{model.comment_set.all()[0].pk}')
    # Create data set
    dataset = models.Dataset()
    dataset.system = models.System.objects.get(pk=request.POST['system'])
    dataset.reference = models.Publication.objects.get(
        pk=request.POST['publication'])
    dataset.label = request.POST['dataset-label']
    if request.POST['primary-property'] != '-1':
        dataset.primary_property = models.Property.objects.get(
            pk=request.POST['primary-property'])
        dataset.primary_unit = models.Unit.objects.get(
            pk=request.POST['primary-unit'])
    if request.POST['secondary-property'] != '-1':
        dataset.secondary_property = models.Property.objects.get(
            pk=request.POST['secondary-property'])
        dataset.secondary_unit = models.Unit.objects.get(
            pk=request.POST['secondary-unit'])
    dataset.visible = 'dataset-visible' in request.POST
    dataset.plotted = 'dataset-plotted' in request.POST
    dataset.experimental = request.POST['is-experimental'] == 'true'
    dataset.dimensionality = (
        3 if (request.POST['is-3d-system'] == 'true') else 2)
    dataset.sample_type = int(request.POST['sample-type'])
    dataset.crystal_system = int(request.POST['crystal-system'])
    dataset.has_files = bool(request.FILES)
    dataset.save(request.user)
    logger.info(f'Create dataset #{dataset.pk}')
    # Synthesis method
    if request.POST['with-synthesis-details'] == 'true':
        synthesis = models.SynthesisMethod(dataset=dataset)
        synthesis.starting_materials = request.POST['starting-materials']
        synthesis.product = request.POST['synthesis-product']
        synthesis.description = request.POST['synthesis-description']
        synthesis.save(request.user)
        logger.info(f'Creating synthesis details #{synthesis.pk}')
        add_comment(synthesis, 'synthesis-comment')
    # Experimental details
    if request.POST['with-experimental-details'] == 'true':
        experimental = models.ExperimentalDetails(dataset=dataset)
        experimental.method = request.POST['experimental-method']
        experimental.description = request.POST['experimental-description']
        experimental.save(request.user)
        logger.info(f'Creating experimental details #{experimental.pk}')
        add_comment(experimental, 'experimental-comment')
    # Computational details
    if request.POST['with-computational-details'] == 'true':
        computational = models.ComputationalDetails(dataset=dataset)
        computational.code = request.POST['code-name']
        computational.level_of_theory = request.POST['level-of-theory']
        computational.xc_functional = request.POST['xc-functional']
        computational.kgrid = request.POST['k-grid']
        computational.relativity_level = request.POST['relativity-level']
        computational.basis = request.POST['basis-sets']
        computational.numerical_accuracy = request.POST['numerical-accuracy']
        computational.save(request.user)
        logger.info(f'Creating computational details #{computational.pk}')
        add_comment(computational, 'computational-comment')
    # Create data series
    dataseries = models.Dataseries(dataset=dataset)
    if 'dataseries-label' in request.POST:
        dataseries.label = request.POST['dataseries-label']
    dataseries.save(request.user)
    # Read in main data
    if dataset.primary_property and dataset.secondary_property:
        input_lines = request.POST['main-data'].split('\n')
        for i_line, line in enumerate(input_lines):
            x_value, y_value = line.split()
            datapoint = models.Datapoint(dataseries=dataseries)
            datapoint.save(request.user)
            # x-values
            numerical_value = models.NumericalValue(datapoint=datapoint)
            numerical_value.qualifier = models.NumericalValue.SECONDARY
            numerical_value.value = float(x_value)
            numerical_value.value_type = models.NumericalValue.ACCURATE
            numerical_value.save(request.user)
            # y-values
            numerical_value = models.NumericalValue(datapoint=datapoint)
            numerical_value.qualifier = models.NumericalValue.PRIMARY
            numerical_value.value = float(y_value)
            numerical_value.value_type = models.NumericalValue.ACCURATE
            numerical_value.save(request.user)
    elif dataset.primary_property:
        input_lines = request.POST['main-data'].split()
        for i_value, value in enumerate(input_lines):
            datapoint = models.Datapoint(dataseries=dataseries)
            datapoint.save(request.user)
            numerical_value = models.NumericalValue(datapoint=datapoint)
            numerical_value.qualifier = models.NumericalValue.PRIMARY
            numerical_value.value = float(value)
            numerical_value.value_type = models.NumericalValue.ACCURATE
            numerical_value.save(request.user)
    # Fixed properties
    fixed_ids = []
    for key in request.POST:
        if key.startswith('fixed-property'):
            fixed_ids.append(key.split('fixed-property')[1])
    for fixed_id in fixed_ids:
        fixed_value = models.NumericalValueFixed(dataseries=dataseries)
        fixed_value.physical_property = models.Property.objects.get(
            name=request.POST[f'fixed-property{fixed_id}'])
        fixed_value.unit = models.Unit.objects.get(
            label=request.POST[f'fixed-unit{fixed_id}'])
        fixed_value.value = float(request.POST[f'fixed-value{fixed_id}'])
        fixed_value.value_type = models.NumericalValueFixed.ACCURATE
        fixed_value.save(request.user)
    # User submitted files
    if dataset.has_files:
        fs = FileSystemStorage(os.path.join(settings.MEDIA_ROOT,
                                            f'uploads/dataset_{dataset.pk}'))
        for file_ in request.FILES.getlist('uploaded-files'):
            fs.save(file_.name, file_)
            logger.info(f'uploading dataset_{dataset.pk}/{file_}')
    # If all went well, let the user know how much data was
    # successfully added
    messages.success(request,
                     f'{len(input_lines)} new data point'
                     f'{"s" if len(input_lines) != 1 else ""} successfully '
                     'added to the database!')
    return redirect(reverse('materials:add_data'))


def toggle_dataset_publish(request, pk, ds):
    dataset = models.Dataset.objects.get(pk=ds)
    dataset.visible = not dataset.visible
    dataset.save(request.user)
    return redirect(reverse('materials:materials_system', args=[pk]))


def toggle_dataset_plotted(request, pk, ds):
    dataset = models.Dataset.objects.get(pk=ds)
    dataset.plotted = not dataset.plotted
    dataset.save(request.user)
    return redirect(reverse('materials:materials_system', args=[pk]))


def download_dataset_files(request, pk):
    loc = os.path.join(settings.MEDIA_ROOT, f'uploads/dataset_{pk}')
    files = os.listdir(loc)
    file_full_paths = [os.path.join(loc, f) for f in files]
    zip_dir = 'files'
    zip_filename = 'files.zip'
    in_memory_object = io.BytesIO()
    zf = zipfile.ZipFile(in_memory_object, 'w')
    for file_path, file_name in zip(file_full_paths, files):
        zf.write(file_path, os.path.join(zip_dir, file_name))
    zf.close()
    response = HttpResponse(in_memory_object.getvalue(),
                            content_type='application/x-zip-compressed')
    response['Content-Disposition'] = f'attachment; filename={zip_filename}'
    return response


def delete_dataset_and_files(request, pk, ds):
    """Delete current data set and all associated files."""
    dataset = models.Dataset.objects.get(pk=ds)
    dataset.delete()
    return redirect(reverse('materials:materials_system', args=[pk]))


class SystemView(generic.DetailView):
    template_name = 'materials/system.html'
    model = models.System


class SpecificSystemView(generic.TemplateView):
    template_name = 'materials/system_specific.html'

    def get(self, request, pk, pk_aa, pk_syn, pk_ee, pk_bs):
        system = models.System.objects.get(pk=pk)
        exciton_emission = system.excitonemission_set.get(pk=pk_ee)
        if system.synthesismethod_set.count() > 0:
            synthesis = system.synthesismethod_set.get(pk=pk_syn)
        else:
            synthesis = None
        if system.atomicpositions_set.count() > 0:
            atomic_positions = system.atomicpositions_set.get(pk=pk_aa)
        else:
            atomic_positions = None
        if system.bandstructure_set.count() > 0:
            band_structure = system.bandstructure_set.get(pk=pk_bs)
        else:
            band_structure = None
        args = {
            'system': system,
            'atomic_positions': atomic_positions,
            'synthesis': synthesis,
            'exciton_emission': exciton_emission,
            'band_structure': band_structure
        }
        return render(request, self.template_name, args)


class SystemUpdateView(generic.UpdateView):
    model = models.System
    template_name = 'materials/system_update_form.html'
    form_class = forms.AddSystem
    success_url = '/materials/{id}'


class AtomicPositionsUpdateView(generic.UpdateView):
    model = models.AtomicPositions
    template_name = 'materials/update_a_pos.html'
    form_class = forms.AddAtomicPositions

    def get_success_url(self):
        pk = self.object.system.pk
        return '/materials/%s/all-a-pos' % str(pk)


class AtomicPositionsDeleteView(generic.DeleteView):
    model = models.AtomicPositions
    template_name = 'materials/delete_a_pos.html'
    form_class = forms.AddAtomicPositions

    def get_success_url(self):
        pk = self.object.system.pk
        return '/materials/%s/all-a-pos' % str(pk)


class SynthesisMethodUpdateView(generic.UpdateView):
    model = models.SynthesisMethodOld
    template_name = 'materials/update_synthesis.html'
    form_class = forms.AddSynthesisMethod

    def get_success_url(self):
        pk = self.object.system.pk
        return '/materials/%s/synthesis' % str(pk)


class SynthesisMethodDeleteView(generic.DeleteView):
    model = models.SynthesisMethodOld
    template_name = 'materials/delete_synthesis.html'
    form_class = forms.AddSynthesisMethod

    def get_success_url(self):
        pk = self.object.system.pk
        return '/materials/%s/synthesis' % str(pk)


class ExcitonEmissionUpdateView(generic.UpdateView):
    model = models.ExcitonEmission
    template_name = 'materials/update_exciton_emission.html'
    form_class = forms.AddExcitonEmission

    def get_success_url(self):
        pk = self.object.system.pk
        return '/materials/%s/exciton_emission' % str(pk)


class ExcitonEmissionDeleteView(generic.DeleteView):
    model = models.ExcitonEmission
    template_name = 'materials/delete_exciton_emission.html'
    form_class = forms.AddExcitonEmission

    def get_success_url(self):
        pk = self.object.system.pk
        return '/materials/%s/exciton_emission' % str(pk)


class BandStructureUpdateView(generic.UpdateView):
    model = models.BandStructure
    template_name = 'materials/update_band_structure.html'
    form_class = forms.AddBandStructure

    def get_success_url(self):
        pk = self.object.system.pk
        return '/materials/%s/band_structure' % str(pk)


class BandStructureDeleteView(generic.DeleteView):
    model = models.BandStructure
    template_name = 'materials/delete_band_structure.html'
    form_class = forms.AddBandStructure

    def get_success_url(self):
        pk = self.object.system.pk
        return '/materials/%s/band_structure' % str(pk)


class PropertyUpdateView(generic.UpdateView):
    model = models.MaterialProperty
    template_name = 'materials/update_material_property.html'
    form_class = forms.AddMaterialProperty

    def get_success_url(self):
        pk = self.object.system.pk
        return '/materials/%s/material_prop' % str(pk)


class PropertyDeleteView(generic.DeleteView):
    model = models.MaterialProperty
    template_name = 'materials/delete_material_property.html'
    form_class = forms.AddMaterialProperty

    def get_success_url(self):
        pk = self.object.system.pk
        return '/materials/%s/material_prop' % str(pk)


def dataset_image(request, pk):
    """Return a png image of the data set."""
    from matplotlib import pyplot
    dataset = models.Dataset.objects.get(pk=pk)
    dataseries = dataset.dataseries_set.all()[0]
    datapoints = dataseries.datapoint_set.all()
    x_values = numpy.zeros(len(datapoints))
    y_values = numpy.zeros(len(datapoints))
    for i_dp, datapoint in enumerate(datapoints):
        x_value = datapoint.numericalvalue_set.get(
            qualifier=models.NumericalValue.SECONDARY)
        x_values[i_dp] = x_value.value
        y_value = datapoint.numericalvalue_set.get(
            qualifier=models.NumericalValue.PRIMARY)
        y_values[i_dp] = y_value.value
    pyplot.plot(x_values, y_values, '-o', linewidth=0.5, ms=3)
    pyplot.title(dataset.label)
    pyplot.ylabel(f'{dataset.primary_property.name}, '
                  f'{dataset.primary_unit.label}')
    pyplot.xlabel(f'{dataset.secondary_property.name}, '
                  f'{dataset.secondary_unit.label}')
    in_memory_object = io.BytesIO()
    pyplot.savefig(in_memory_object, format='png')
    image = in_memory_object.getvalue()
    pyplot.close()
    in_memory_object.close()
    return HttpResponse(image, content_type='image/png')


def dataset_data(request, pk):
    """Return the data set as a text file."""
    dataset = models.Dataset.objects.get(pk=pk)
    dataseries = dataset.dataseries_set.all()[0]
    datapoints = dataseries.datapoint_set.all()
    text = ''
    for i_dp, datapoint in enumerate(datapoints):
        x_value = datapoint.numericalvalue_set.get(
            qualifier=models.NumericalValue.SECONDARY)
        y_value = datapoint.numericalvalue_set.get(
            qualifier=models.NumericalValue.PRIMARY)
        text += f'{x_value.value} {y_value.value}\n'
    return HttpResponse(text, content_type='text/plain')


def publication_data(request, pk):
    """Return a key-value representation of the data set.

    The representation conforms to the one used in Qresp
    (http://qresp.org/).

    """
    data = {}
    data['info'] = {
        'downloadPath': request.get_host(),
        'fileServerPath': '',
        'folderAbsolutePath': '',
        'insertedBy': {
            'firstName': '',
            'lastName': '',
            'middleName': ''
        },
        'isPublic': 'true',
        'notebookFile': '',
        'notebookPath': '',
        'serverPath': request.get_host(),
        'timeStamp': '2017-06-22 18:19:02'
    }
    publication = models.Publication.objects.get(pk=pk)
    data['reference'] = {}
    data['reference']['journal'] = {
        'abbrevName': publication.journal,
        'fullName': publication.journal,
        'kind': 'journal',
        'page': publication.pages_start,
        'publishedAbstract': '',
        'publishedDate': '',
        'receivedDate': '',
        'title': publication.title,
        'volume': publication.vol,
        'year': publication.year,
    }
    data['reference']['authors'] = []
    for author in publication.author_set.all():
        data['reference']['authors'].append({
            'firstname': author.first_name,
            'lastname': author.last_name,
        })
    data['PIs'] = []
    data['PIs'].append({'firstname': '', 'lastname': ''})
    data['collections'] = []
    data['collections'].append('')
    datasets = publication.dataset_set.all()
    data['charts'] = []
    dataset_counter = 1
    for dataset in datasets:
        chart = {
            'caption': dataset.label,
            'files': [f'/materials/dataset-{dataset.pk}/data.txt'],
            'id': '',
            'imageFile': f'/materials/dataset-{dataset.pk}/image.png',
            'kind': 'figure' if dataset.plotted else 'table',
            'notebookFile': '',
            'number': dataset_counter,
            'properties': [],
        }
        if dataset.secondary_property:
            chart['properties'].append(dataset.secondary_property.name)
        if dataset.primary_property:
            chart['properties'].append(dataset.primary_property.name)
        loc = os.path.join(settings.MEDIA_ROOT,
                           f'uploads/dataset_{dataset.pk}')
        for file_ in os.listdir(loc):
            chart['files'].append(settings.MEDIA_URL +
                                  f'uploads/dataset_{dataset.pk}/{file_}')
        data['charts'].append(chart)
        dataset_counter += 1
    return JsonResponse(data)
