<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_import_csv\Kernel;

use Drupal\taxonomy\Entity\Term;
use Drupal\text\Plugin\Field\FieldType\TextLongItem;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests for taxonomy term CSV importers.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class TermCsvImportTest extends CsvImportTestBase {

  /**
   * {@inheritdoc}
   */
  public function setUp(): void {
    parent::setUp();

    // Create parent term to test asset_lookup.
    $term = Term::create(['name' => 'Sheep', 'vid' => 'animal_type']);
    $term->save();
  }

  /**
   * Test term CSV importer.
   */
  public function testTermCsvImport() {

    // Run the CSV import.
    $this->importCsv('animal-types.csv', 'csv_taxonomy_term:animal_type');

    // Confirm that terms have been created with the expected values
    // (in addition to the one we created in setUp() above).
    $terms = Term::loadMultiple();
    $this->assertCount(4, $terms);
    $expected_values = [
      2 => [
        'name' => 'Cow',
        'description' => 'Cow description',
        'test_config_field' => 'foo',
      ],
      3 => [
        'name' => 'Pig',
        'description' => 'Pig description',
        'test_config_field' => 'bar',
      ],
      4 => [
        'name' => 'Galway',
        'description' => 'Large polled white-faced sheep',
        'parent' => 'Sheep',
        'test_config_field' => '',
      ],
    ];
    foreach ($terms as $id => $term) {
      // Skip terms created in setup().
      if ($id <= 1) {
        continue;
      }
      $this->assertEquals('animal_type', $term->bundle());
      $this->assertEquals($expected_values[$id]['name'], $term->label());
      $this->assertEquals($expected_values[$id]['description'], $term->getDescription());
      $this->assertInstanceOf(TextLongItem::class, $term->get('description')->first());
      $this->assertEquals('default', $term->get('description')->first()->format);
      if (!empty($expected_values[$id]['parent'])) {
        $this->assertEquals($expected_values[$id]['parent'], $term->get('parent')->referencedEntities()[0]->label());
      }
      else {
        $this->assertEmpty($term->get('parent')->referencedEntities());
      }
      $this->assertEquals($expected_values[$id]['test_config_field'], $term->get('test_config_field')->value);
    }
  }

}
