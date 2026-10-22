<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_image\Functional;

use Drupal\Core\File\FileExists;
use Drupal\Tests\farm_test\Functional\FarmBrowserTestBase;
use Drupal\image\Entity\ImageStyle;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests for the farm_image image effects.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class ImageEffectsTest extends FarmBrowserTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'farm_image',
  ];

  /**
   * Run all tests.
   */
  public function testAll() {
    $this->doTestEffectAdded();
    $this->doTestAutoOrient();
  }

  /**
   * Tests that the auto-orient effect is added to core styles.
   */
  public function doTestEffectAdded(): void {

    // Load the core image styles and confirm that they contain the auto-orient
    // effect.
    $styles = [
      'large',
      'medium',
      'thumbnail',
      'wide',
    ];
    foreach ($styles as $style) {
      $image_style = ImageStyle::load($style);
      $this->assertNotEmpty(array_filter([...$image_style->getEffects()], function ($effect) {
        return $effect->getPluginId() === 'farm_image_auto_orient';
      }));
    }
  }

  /**
   * Tests the auto-orient effect.
   */
  public function doTestAutoOrient(): void {

    // Create a test image style with the auto-orient effect.
    $image_style = ImageStyle::create([
      'name' => 'test',
      'label' => 'Test',
    ]);
    $this->assertEquals(SAVED_NEW, $image_style->save());
    $image_style->addImageEffect([
      'id' => 'farm_image_auto_orient',
      'weight' => 0,
    ]);
    $this->assertEquals(SAVED_UPDATED, $image_style->save());

    // Create a copy of a test image file in public files directory.
    $test_uri = 'public://rotate90cw.jpg';
    $file_path = \Drupal::service('extension.list.module')->getPath('farm_image') . '/tests/files/rotate90cw.jpg';
    \Drupal::service('file_system')->copy($file_path, $test_uri, FileExists::Replace);
    $this->assertFileExists($test_uri);

    // Confirm that the original image is vertically oriented.
    $image_size = getimagesize($test_uri);
    $this->assertEquals('600', $image_size[1]);
    $this->assertEquals('400', $image_size[0]);

    // Execute the image style on the test image via a GET request.
    $derivative_uri = 'public://styles/test/public/rotate90cw.jpg';
    $this->assertFileDoesNotExist($derivative_uri);
    $url = \Drupal::service('file_url_generator')->transformRelative($image_style->buildUrl($test_uri));
    $this->drupalGet($this->getAbsoluteUrl($url));
    $this->assertSession()->statusCodeEquals(200);
    $this->assertFileExists($derivative_uri);

    // Confirm that the derivative file is horizontally oriented.
    $image_size = getimagesize($derivative_uri);
    $this->assertEquals('400', $image_size[1]);
    $this->assertEquals('600', $image_size[0]);
  }

}
