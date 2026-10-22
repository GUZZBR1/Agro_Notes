<?php

declare(strict_types=1);

namespace Drupal\Tests\asset\Functional;

use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\asset\Entity\Asset;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests the asset CRUD.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class AssetCRUDTest extends AssetTestBase {

  use StringTranslationTrait;

  /**
   * Run all tests.
   */
  public function testAll() {
    $this->doTestFieldsVisibility();
    $this->doTestCreateAsset();
    $this->doTestViewAsset();
    $this->doTestEditAsset();
    $this->doTestDeleteAsset();
    $this->doTestArchiveAsset();
    $this->doTestArchiveAssetViaTimestamp();
  }

  /**
   * Fields are displayed correctly.
   */
  public function doTestFieldsVisibility() {
    $this->drupalGet('asset/add/default');
    $assert_session = $this->assertSession();
    $assert_session->statusCodeEquals(200);
    $assert_session->fieldExists('name[0][value]');
    $assert_session->fieldExists('revision_log_message[0][value]');
    $assert_session->fieldExists('uid[0][target_id]');
    $assert_session->fieldExists('created[0][value][date]');
    $assert_session->fieldExists('created[0][value][time]');
  }

  /**
   * Create asset entity.
   */
  public function doTestCreateAsset() {
    $assert_session = $this->assertSession();
    $name = $this->randomMachineName();
    $edit = [
      'name[0][value]' => $name,
    ];

    $this->drupalGet('asset/add/default');
    $this->submitForm($edit, 'Save');

    $result = \Drupal::entityTypeManager()
      ->getStorage('asset')
      ->getQuery()
      ->accessCheck(TRUE)
      ->range(0, 1)
      ->execute();
    $asset_id = reset($result);
    $asset = Asset::load($asset_id);
    $this->assertEquals($asset->get('name')->value, $name, 'asset has been saved.');

    $assert_session->pageTextContains("Saved asset: $name");
    $assert_session->pageTextContains($name);
  }

  /**
   * Display asset entity.
   */
  public function doTestViewAsset() {
    $edit = [
      'name' => $this->randomMachineName(),
      'created' => \Drupal::time()->getRequestTime(),
    ];
    $asset = $this->createAssetEntity($edit);
    $asset->save();

    $this->drupalGet($asset->toUrl('canonical'));
    $this->assertSession()->statusCodeEquals(200);

    $this->assertSession()->pageTextContains($edit['name']);
    $this->assertSession()->responseContains(\Drupal::service('date.formatter')->format(\Drupal::time()->getRequestTime()));
  }

  /**
   * Edit asset entity.
   */
  public function doTestEditAsset() {
    $asset = $this->createAssetEntity();
    $asset->save();

    $edit = [
      'name[0][value]' => $this->randomMachineName(),
    ];
    $this->drupalGet($asset->toUrl('edit-form'));
    $this->submitForm($edit, 'Save');
    $this->assertSession()->pageTextContains($edit['name[0][value]']);
  }

  /**
   * Delete asset entity.
   */
  public function doTestDeleteAsset() {
    $asset = $this->createAssetEntity();
    $asset->save();

    $label = $asset->getName();
    $asset_id = $asset->id();

    $this->drupalGet($asset->toUrl('delete-form'));
    $this->submitForm([], 'Delete');
    $this->assertSession()->responseContains($this->t('The @entity-type %label has been deleted.', [
      '@entity-type' => $asset->getEntityType()->getSingularLabel(),
      '%label' => $label,
    ]));
    $this->assertNull(Asset::load($asset_id));
  }

  /**
   * Asset archiving.
   */
  public function doTestArchiveAsset() {
    $asset = $this->createAssetEntity();
    $asset->save();

    $this->assertFalse($asset->get('archived')->value, 'New assets are not archived by default');
    $this->assertNull($asset->get('last_archived')->value, 'Archived timestamp is null by default');

    $asset->set('archived', TRUE);
    $asset->save();

    $this->assertTrue($asset->get('archived')->value, 'Assets can be archived');
    $this->assertNotNull($asset->get('last_archived')->value, 'Archived timestamp is saved');

    $asset->set('archived', FALSE);
    $asset->save();

    $this->assertFalse($asset->get('archived')->value, 'Assets can be unarchived');
    $this->assertNull($asset->get('last_archived')->value, 'Unarchived assets have a null timestamp');

    $asset->set('archived', TRUE);
    $asset->set('last_archived', '2021-07-17T19:45:49+00:00');
    $asset->save();

    $this->assertTrue($asset->get('archived')->value, 'Assets can be archived with explicit timestamp');
    $this->assertEquals($asset->get('last_archived')->value, '2021-07-17T19:45:49+00:00', 'Explicit archived timestamp is saved');
  }

  /**
   * Asset archiving/unarchiving via timestamp.
   */
  public function doTestArchiveAssetViaTimestamp() {
    $asset = $this->createAssetEntity();
    $asset->save();

    $this->assertFalse($asset->get('archived')->value, 'New assets are not archived by default');
    $this->assertNull($asset->get('last_archived')->value, 'Archived timestamp is null by default');

    $asset->set('last_archived', '2021-07-17T19:45:49+00:00');
    $asset->save();

    $this->assertTrue($asset->get('archived')->value, 'Assets can be archived');
    $this->assertEquals($asset->get('last_archived')->value, '2021-07-17T19:45:49+00:00', 'Archived timestamp is saved');

    $asset->set('last_archived', NULL);
    $asset->save();

    $this->assertFalse($asset->get('archived')->value, 'Assets can be unarchived');
    $this->assertNull($asset->get('last_archived')->value, 'Unarchived asset has a null timestamp');
  }

}
