class PowerOfAttorneyAPITest(APITestCase):
    """Test cases for Power of Attorney API endpoints."""

    def setUp(self):
        """Set up test client and test data."""
        self.client = APIClient()
        self.user = self._create_test_user()
        self.client.force_authenticate(user=self.user)
        
        self.poa_data = {
            'document_date': '2025-03-04',
            'company_name': 'Test Company Ltd',
            'company_address': '123 Test Street, Test City',
            'company_po_box': 'P.O. Box 12345',
            'attorney_name': 'John Doe',
            'attorney_po_box': 'P.O. Box 67890',
            'attorney_address': '456 Attorney Ave, Test City',
            'tender_number': 'TEST/2025/001/ABC',
            'tender_description': 'Test Tender Description',
            'tender_beneficiary': 'Test Beneficiary Org',
            'witness_name': 'Jane Witness',
            'witness_po_box': 'P.O. Box 54321',
            'witness_title': 'Notary Public',
            'witness_address': '789 Witness Way, Test City'
        }
        self.poa = PowerOfAttorney.objects.create(**self.poa_data)

        # Debug URL resolution
        print("Resolved URLs:")
        print(f"List: {reverse('power-of-attorney-list')}")
        print(f"Detail: {reverse('power-of-attorney-detail', kwargs={'slug': self.poa.slug})}")
        print(f"Generate: {reverse('power-of-attorney-generate-document', kwargs={'slug': self.poa.slug})}")

    def _create_test_user(self):
        """Helper method to create test user using CustomUser."""
        return CustomUser.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_list_power_of_attorney(self):
        """Test listing all power of attorney documents."""
        url = reverse('power-of-attorney-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['slug'], self.poa.slug)

    def test_create_power_of_attorney(self):
        """Test creating new power of attorney document."""
        url = reverse('power-of-attorney-list')
        new_data = {
            **self.poa_data,
            'tender_number': 'TEST/2025/002/DEF'
        }
        response = self.client.post(url, new_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PowerOfAttorney.objects.count(), 2)
        self.assertEqual(response.data['tender_number'], 'TEST/2025/002/DEF')

    def test_retrieve_power_of_attorney(self):
        """Test retrieving specific power of attorney document."""
        url = reverse('power-of-attorney-detail', kwargs={'slug': self.poa.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['tender_number'], self.poa.tender_number)
        self.assertEqual(response.data['slug'], self.poa.slug)

    def test_update_power_of_attorney(self):
        """Test updating existing power of attorney document."""
        url = reverse('power-of-attorney-detail', kwargs={'slug': self.poa.slug})
        update_data = {**self.poa_data, 'tender_description': 'Updated Description'}
        response = self.client.put(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.poa.refresh_from_db()
        self.assertEqual(self.poa.tender_description, 'Updated Description')

    def test_partial_update_power_of_attorney(self):
        """Test partial update of power of attorney document."""
        url = reverse('power-of-attorney-detail', kwargs={'slug': self.poa.slug})
        update_data = {'tender_description': 'Partially Updated Description'}
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.poa.refresh_from_db()
        self.assertEqual(self.poa.tender_description, 'Partially Updated Description')

    def test_delete_power_of_attorney(self):
        """Test deleting power of attorney document."""
        url = reverse('power-of-attorney-detail', kwargs={'slug': self.poa.slug})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PowerOfAttorney.objects.count(), 0)

    def test_generate_document_docx(self):
        """Test generating Word document."""
        if not DOCX_AVAILABLE:
            self.skipTest("python-docx not installed")
        
        url = reverse('power-of-attorney-generate-document', kwargs={'slug': self.poa.slug})
        print(f"Testing Docx URL: {url}?format=docx")
        response = self.client.get(f"{url}?format=docx")
        if response.status_code != status.HTTP_200_OK:
            print(f"Docx generation failed: Status {response.status_code}, Content: {response.content.decode()}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        self.assertIn('attachment; filename=poa_', response['Content-Disposition'])
        if DOCX_AVAILABLE:
            doc_content = BytesIO(response.content)
            doc = Document(doc_content)
            content = ' '.join([p.text for p in doc.paragraphs])
            self.assertIn(self.poa.company_name, content)

    def test_generate_document_pdf(self):
        """Test generating PDF document."""
        if not REPORTLAB_AVAILABLE:
            self.skipTest("reportlab not installed")
        
        url = reverse('power-of-attorney-generate-document', kwargs={'slug': self.poa.slug})
        print(f"Testing PDF URL: {url}?format=pdf")
        response = self.client.get(f"{url}?format=pdf")
        if response.status_code != status.HTTP_200_OK:
            print(f"PDF generation failed: Status {response.status_code}, Content: {response.content.decode()}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename=poa_', response['Content-Disposition'])

    def test_generate_document_invalid_format(self):
        """Test generating document with invalid format."""
        url = reverse('power-of-attorney-generate-document', kwargs={'slug': self.poa.slug})
        print(f"Testing Invalid Format URL: {url}?format=invalid")
        response = self.client.get(f"{url}?format=invalid")
        if response.status_code != status.HTTP_400_BAD_REQUEST:
            print(f"Invalid format test failed: Status {response.status_code}, Content: {response.content.decode()}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_unauthenticated_access(self):
        """Test access without authentication."""
        self.client.force_authenticate(user=None)
        url = reverse('power-of-attorney-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_tender_number_format(self):
        """Test creating document with invalid tender number format."""
        url = reverse('power-of-attorney-list')
        invalid_data = {
            **self.poa_data,
            'tender_number': 'INVALID@FORMAT',
            'company_name': 'Different Company'
        }
        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tender_number', response.data)

    def test_url_resolution(self):
        """Test that all expected URLs can be resolved."""
        list_url = reverse('power-of-attorney-list')
        detail_url = reverse('power-of-attorney-detail', kwargs={'slug': self.poa.slug})
        generate_url = reverse('power-of-attorney-generate-document', kwargs={'slug': self.poa.slug})
        
        self.assertEqual(resolve(list_url).url_name, 'power-of-attorney-list')
        self.assertEqual(resolve(detail_url).url_name, 'power-of-attorney-detail')
        self.assertEqual(resolve(generate_url).url_name, 'power-of-attorney-generate-document')